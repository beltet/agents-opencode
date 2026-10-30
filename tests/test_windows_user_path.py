"""Windows user PATH tests: no registry access or real installation on any OS."""

import contextlib
import ctypes
import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("path_installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
BIN = r"C:\Users\Åsa 日本語\Local AppData\agents-opencode\bin"


def registry(value="", kind=1, missing=False, missing_key=False):
    reg = mock.Mock(REG_SZ=1, REG_EXPAND_SZ=2, HKEY_CURRENT_USER=123,
                    KEY_QUERY_VALUE=1, KEY_SET_VALUE=2)
    key = mock.MagicMock()
    key.__enter__.return_value = key
    reg.OpenKey.return_value = key
    reg.CreateKeyEx.return_value = key
    if missing_key:
        reg.OpenKey.side_effect = FileNotFoundError()
    if missing:
        reg.QueryValueEx.side_effect = FileNotFoundError()
    else:
        reg.QueryValueEx.return_value = value, kind
    return reg


class UserPathTests(unittest.TestCase):
    def add(self, reg, **kwargs):
        kwargs.setdefault("notify", mock.Mock(return_value=True))
        return installer.add_windows_user_path(BIN, registry=reg, **kwargs)

    def test_missing_empty_and_missing_key_never_copy_process_path(self):
        for kwargs in ({}, {"missing": True}, {"missing_key": True}):
            with self.subTest(kwargs=kwargs), mock.patch.dict("os.environ", {"PATH": "inherited-secret"}):
                reg = registry(**kwargs)
                self.assertEqual(self.add(reg), (True, True))
                reg.SetValueEx.assert_called_once_with(reg.CreateKeyEx.return_value, "Path", 0, 1, BIN)
                reg.CreateKeyEx.assert_called_once_with(123, "Environment", 0, 2)

    def test_original_text_type_and_empty_entries_are_preserved(self):
        original = '  "C:\\Old Folder" ;%UNKNOWN%;C:\\日本語;;'
        for kind in (1, 2):
            with self.subTest(kind=kind):
                reg = registry(original, kind)
                self.assertEqual(self.add(reg, expand=lambda s: s), (True, True))
                self.assertEqual(reg.SetValueEx.call_args.args[3:], (kind, original + ";" + BIN))

    def test_duplicate_quotes_case_whitespace_slashes_and_dot_segments(self):
        for entry in (BIN, '  "' + BIN.upper() + '\\"  ',
                      BIN.replace("\\", "/") + "/", BIN + r"\child\.."):
            with self.subTest(entry=entry):
                reg = registry("C:\\else;" + entry + ";")
                notify = mock.Mock()
                self.assertEqual(self.add(reg, notify=notify), (False, True))
                reg.SetValueEx.assert_not_called()
                reg.CreateKeyEx.assert_not_called()
                notify.assert_not_called()

    def test_repeat_install_does_not_rewrite(self):
        reg = registry("C:\\old")
        self.add(reg)
        saved = reg.SetValueEx.call_args.args[-1]
        reg.QueryValueEx.return_value = saved, 1
        self.assertEqual(self.add(reg), (False, True))
        self.assertEqual(reg.SetValueEx.call_count, 1)

    def test_expansion_only_for_expand_sz_using_injected_windows_semantics(self):
        # Case-insensitive %VAR%; unknown variables remain literal (no $VAR expansion).
        def expand(s):
            return s.replace("%lOcAlApPdAtA%", r"C:\Users\Åsa 日本語\Local AppData")

        text = r"%lOcAlApPdAtA%\agents-opencode\bin"
        reg = registry(text, 2)
        self.assertEqual(self.add(reg, expand=expand), (False, True))
        reg.SetValueEx.assert_not_called()
        reg = registry(text, 1)
        forbidden = mock.Mock(side_effect=AssertionError("REG_SZ must not expand"))
        self.assertEqual(self.add(reg, expand=forbidden), (True, True))
        forbidden.assert_not_called()
        reg = registry(text, 2)
        reg.ExpandEnvironmentStrings.side_effect = expand
        self.assertEqual(self.add(reg), (False, True))
        reg.ExpandEnvironmentStrings.assert_called()

    def test_unsupported_types_or_non_string_never_write(self):
        for value, kind in ((42, 4), (["one"], 7), ("text", 3), (42, 1)):
            with self.subTest(value=value, kind=kind):
                reg = registry(value, kind)
                with self.assertRaisesRegex(OSError, "REG_SZ or REG_EXPAND_SZ"):
                    self.add(reg)
                reg.SetValueEx.assert_not_called()
                reg.CreateKeyEx.assert_not_called()

    def test_access_denied_propagates_without_notification(self):
        for operation in ("OpenKey", "CreateKeyEx", "SetValueEx"):
            with self.subTest(operation=operation):
                reg = registry()
                getattr(reg, operation).side_effect = PermissionError("Access denied")
                notify = mock.Mock()
                with self.assertRaisesRegex(PermissionError, "Access denied"):
                    self.add(reg, notify=notify)
                notify.assert_not_called()

    def test_broadcast_failure_keeps_written_value(self):
        for notify in (mock.Mock(return_value=False), mock.Mock(side_effect=OSError("timeout"))):
            reg = registry()
            self.assertEqual(self.add(reg, notify=notify), (True, False))
            reg.SetValueEx.assert_called_once()

    def test_broadcast_unicode_pointer_signatures_and_timeout(self):
        def send(hwnd, message, wparam, lparam, flags, timeout, result):
            self.assertEqual((hwnd, message, wparam, flags, timeout), (0xFFFF, 0x1A, 0, 2, 2000))
            self.assertEqual(ctypes.wstring_at(lparam), "Environment")
            return 1

        function = mock.Mock(side_effect=send)
        with mock.patch.object(ctypes, "WinDLL", create=True,
                               return_value=types.SimpleNamespace(SendMessageTimeoutW=function)):
            self.assertTrue(installer.broadcast_environment_change())
        self.assertIs(function.restype, ctypes.c_ssize_t)
        self.assertIs(function.argtypes[2], ctypes.c_size_t)
        self.assertIs(function.argtypes[3], ctypes.c_ssize_t)
        self.assertIs(function.argtypes[-1], ctypes.POINTER(ctypes.c_size_t))


class MainPathTests(unittest.TestCase):
    def run_main(self, platform="win32", lang="en", extra=(), failure=None, notified=True):
        destination, bin_dir = ROOT / "fake-install", ROOT / "fake-install/bin"
        output, errors = io.StringIO(), io.StringIO()
        translation = types.SimpleNamespace(set_language=lambda lang: None,
            tr=lambda sv, en: sv if lang == "sv" else en)
        old_path = sys.path[:]
        try:
            # sys.platform is patched, not os.name: pathlib keeps the host path class.
            with mock.patch.object(sys, "platform", platform), \
                 mock.patch.dict(sys.modules, {"i18n": translation}), \
                 mock.patch.object(installer, "install_paths", return_value=(destination, bin_dir)), \
                 mock.patch.object(installer, "install", return_value=(bin_dir / "agents-opencode.cmd", None)) as install, \
                 mock.patch.object(installer, "add_windows_user_path", side_effect=failure,
                                   return_value=(True, notified)) as add, \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = installer.main(["--lang", lang, *extra])
                install.assert_called_once()
        finally:
            sys.path[:] = old_path
        return status, output.getvalue(), errors.getvalue(), add

    def test_windows_default_and_opt_out_and_non_windows(self):
        status, out, err, add = self.run_main()
        self.assertEqual(status, 0)
        add.assert_called_once_with(ROOT / "fake-install/bin")
        self.assertIn("Open a new terminal", out)
        self.assertIn("parent process PATH", out)
        self.assertEqual(err, "")
        for kwargs in ({"extra": ["--no-path"]}, {"platform": "linux"}):
            status, out, err, add = self.run_main(**kwargs)
            self.assertEqual(status, 0)
            add.assert_not_called()

    def test_failure_bilingual_retains_install_and_manual_location(self):
        for lang, expected in (("en", "Installation retained"), ("sv", "Installationen finns kvar")):
            status, out, err, _ = self.run_main(lang=lang, failure=PermissionError("Access denied"))
            self.assertEqual(status, 1)
            self.assertIn(expected, err)
            self.assertIn(str(ROOT / "fake-install/bin"), err)
            self.assertIn("Access denied", err)
            self.assertIn("agents-opencode.cmd", out)

    def test_notification_warning_bilingual_is_success(self):
        for lang, expected in (("en", "Warning:"), ("sv", "Varning:")):
            status, out, err, _ = self.run_main(lang=lang, notified=False)
            self.assertEqual(status, 0)
            self.assertIn(expected, err)


if __name__ == "__main__":
    unittest.main()
