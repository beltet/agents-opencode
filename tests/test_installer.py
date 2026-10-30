"""Offline central-installer checks; all installation paths are temporary."""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("central_installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source package å"
        (self.source / "lib" / "profiles").mkdir(parents=True)
        (self.source / "lib" / "manager.py").write_text("# new manager\n", encoding="utf-8")
        (self.source / "lib" / "profiles" / "sample.md").write_text("profile\n")
        for name in ("agents-opencode", "agents-opencode.cmd"):
            (self.source / name).write_bytes((ROOT / name).read_bytes())
        (self.source / "AGENT_CAST.md").write_text("Product cast\n")
        (self.source / "START_HAR.md").write_text("Swedish start guide\n")
        (self.source / "START_HERE.md").write_text("English start guide\n")
        self.destination = self.root / "data space 日本語" / "agents-opencode"
        self.bin = self.root / "bin space ö"

    def install(self, platform="linux"):
        bin_dir = self.destination / "bin" if platform == "win32" else self.bin
        return installer.install(self.source, self.destination, bin_dir, platform)

    def test_linux_paths_default_and_xdg(self):
        home = self.root / "home"
        self.assertEqual(installer.install_paths("linux", {}, home), (
            home / ".local/share/agents-opencode", home / ".local/bin"))
        env = {"XDG_DATA_HOME": str(self.root / "data"), "XDG_BIN_HOME": str(self.bin)}
        self.assertEqual(installer.install_paths("linux", env, home), (
            self.root / "data/agents-opencode", self.bin))
        self.assertEqual(installer.install_paths("linux", {"XDG_DATA_HOME": "", "XDG_BIN_HOME": ""}, home),
                         installer.install_paths("linux", {}, home))

    def test_windows_paths_ignore_xdg(self):
        local = self.root / "Local AppData å"
        env = {"LOCALAPPDATA": str(local), "XDG_DATA_HOME": "unused", "XDG_BIN_HOME": "unused"}
        self.assertEqual(installer.install_paths("win32", env, self.root), (
            local / "agents-opencode", local / "agents-opencode/bin"))
        self.assertEqual(installer.install_paths("win32", {}, self.root), (
            self.root / "AppData/Local/agents-opencode", self.root / "AppData/Local/agents-opencode/bin"))

    def test_fresh_install_spaces_unicode_and_product_doc(self):
        launcher, backup = self.install()
        self.assertIsNone(backup)
        self.assertEqual(launcher, self.bin / "agents-opencode")
        self.assertTrue(launcher.stat().st_mode & 0o111)
        self.assertEqual((self.destination / "AGENT_CAST.md").read_text(), "Product cast\n")
        self.assertEqual((self.destination / "START_HAR.md").read_text(), "Swedish start guide\n")
        self.assertEqual((self.destination / "START_HERE.md").read_text(), "English start guide\n")
        self.assertEqual((self.destination / "lib/profiles/sample.md").read_text(), "profile\n")
        self.assertEqual(list(self.destination.parent.glob(".agents-opencode-*")), [])

    def test_upgrade_preserves_custom_profiles_and_unrelated_projects(self):
        for platform in ("linux", "win32"):
            with self.subTest(platform=platform):
                self.install(platform)
                custom = self.destination / "custom-profiles"
                custom.mkdir(exist_ok=True)
                (custom / "min roll ö.md").write_text("personal profile\n", encoding="utf-8")
                project = self.root / "unrelated-project"
                project.mkdir(exist_ok=True)
                (project / "opencode.json").write_text('{"model":"mine"}\n')
                (self.destination / "personal-notes.txt").write_text("keep me\n")
                (self.destination / "lib/obsolete.py").write_text("old code\n")
                self.install(platform)
                self.assertEqual((custom / "min roll ö.md").read_text(encoding="utf-8"), "personal profile\n")
                self.assertEqual((project / "opencode.json").read_text(), '{"model":"mine"}\n')
                self.assertEqual((self.destination / "personal-notes.txt").read_text(), "keep me\n")
                self.assertFalse((self.destination / "lib/obsolete.py").exists())

    def test_windows_install_uses_cmd_launcher(self):
        launcher, _ = self.install("win32")
        self.assertEqual(launcher, self.destination / "bin/agents-opencode.cmd")
        self.assertEqual(launcher.read_bytes(), (ROOT / "agents-opencode.cmd").read_bytes())

    def test_unrecognized_destination_is_untouched(self):
        self.destination.mkdir(parents=True)
        keep = self.destination / "important.txt"
        keep.write_text("user data")
        with self.assertRaisesRegex(OSError, "unrecognized"):
            self.install()
        self.assertEqual(keep.read_text(), "user data")

    def test_install_cannot_replace_source_ancestor(self):
        with self.assertRaises(OSError):
            installer.install(self.source, self.source, self.bin, "linux")
        self.assertEqual((self.source / "lib/manager.py").read_text(), "# new manager\n")

    def test_staging_failure_leaves_old_install_and_launcher(self):
        self.install()
        manager = self.destination / "lib/manager.py"
        manager.write_text("old version")
        launcher = self.bin / "agents-opencode"
        launcher.write_text("old launcher")
        with mock.patch.object(installer.shutil, "copytree", side_effect=OSError("copy failed")):
            with self.assertRaisesRegex(OSError, "copy failed"):
                self.install()
        self.assertEqual(manager.read_text(), "old version")
        self.assertEqual(launcher.read_text(), "old launcher")
        self.assertEqual(list(self.destination.parent.glob(".agents-opencode-*")), [])

    def test_promotion_failure_restores_old_tree(self):
        self.install()
        manager = self.destination / "lib/manager.py"
        manager.write_text("old version")
        rename = Path.rename

        def fail_promotion(path, target):
            if path.name.startswith(".agents-opencode-new-") and not path.name.endswith(".previous"):
                raise OSError("promotion failed")
            return rename(path, target)

        with mock.patch.object(Path, "rename", fail_promotion):
            with self.assertRaisesRegex(OSError, "promotion failed"):
                self.install()
        self.assertEqual(manager.read_text(), "old version")
        self.assertEqual(list(self.destination.parent.glob(".agents-opencode-*")), [])

    def test_launcher_failure_rolls_back_on_both_platforms(self):
        for platform in ("linux", "win32"):
            with self.subTest(platform=platform):
                launcher, _ = self.install(platform)
                manager = self.destination / "lib/manager.py"
                manager.write_text("old version")
                launcher.write_text("old launcher")
                custom = self.destination / "custom-profiles"
                custom.mkdir(exist_ok=True)
                (custom / "mine.md").write_text("mine")
                with mock.patch.object(installer.os, "replace", side_effect=OSError("publish failed")):
                    with self.assertRaisesRegex(OSError, "publish failed"):
                        self.install(platform)
                self.assertEqual(manager.read_text(), "old version")
                self.assertEqual(launcher.read_text(), "old launcher")
                self.assertEqual((custom / "mine.md").read_text(), "mine")
                self.assertEqual(list(self.destination.parent.glob(".agents-opencode-*")), [])

    def test_first_install_publication_failure_removes_partial_package(self):
        with mock.patch.object(installer.os, "replace", side_effect=OSError("publish failed")):
            with self.assertRaises(OSError):
                self.install("win32")
        self.assertFalse(self.destination.exists())

    def test_rollback_move_failure_preserves_original_error_and_previous_data(self):
        launcher, _ = self.install()
        (self.destination / "lib/manager.py").write_text("old version")
        custom = self.destination / "custom-profiles"
        custom.mkdir()
        (custom / "mine.md").write_text("irreplaceable profile")
        launcher.write_text("old launcher")
        rename = Path.rename
        restoration_attempts = []

        def fail_rollback_move(path, target):
            if path == self.destination and Path(target).name.startswith(".agents-opencode-new-") \
                    and not Path(target).name.endswith(".previous"):
                raise OSError("rollback move failed")
            if path.name.endswith(".previous"):
                restoration_attempts.append(path)
            return rename(path, target)

        original = OSError("publish failed")
        output = io.StringIO()
        with mock.patch.object(installer.os, "replace", side_effect=original), \
             mock.patch.object(Path, "rename", fail_rollback_move), \
             contextlib.redirect_stderr(output):
            with self.assertRaises(OSError) as raised:
                self.install()
        self.assertIs(raised.exception, original)
        previous, = self.destination.parent.glob(".agents-opencode-new-*.previous")
        self.assertEqual(restoration_attempts, [previous])
        self.assertEqual((previous / "lib/manager.py").read_text(), "old version")
        self.assertEqual((previous / "custom-profiles/mine.md").read_text(), "irreplaceable profile")
        self.assertEqual(launcher.read_text(), "old launcher")
        self.assertIn("rollback move failed", output.getvalue())
        self.assertIn("Previous installation retained for manual recovery at: " + str(previous),
                      output.getvalue())

    def test_backup_cleanup_failure_retains_successful_install(self):
        self.install()
        rmtree = installer.shutil.rmtree

        def fail_backup_cleanup(path, *args, **kwargs):
            if Path(path).name.endswith(".previous"):
                raise OSError("backup is busy")
            return rmtree(path, *args, **kwargs)

        with mock.patch.object(installer.shutil, "rmtree", side_effect=fail_backup_cleanup):
            launcher, backup = self.install()
        self.assertTrue(launcher.is_file())
        self.assertTrue((backup / "lib/manager.py").is_file())
        self.assertEqual((self.destination / "lib/manager.py").read_text(), "# new manager\n")

    @unittest.skipIf(sys.platform == "win32", "Symlink privileges vary on Windows")
    def test_destination_symlink_does_not_touch_target(self):
        self.destination.parent.mkdir(parents=True)
        self.destination.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(OSError, "symlink"):
            self.install()
        self.assertEqual((self.source / "lib/manager.py").read_text(), "# new manager\n")

    def test_language_is_selected_before_installation_and_guidance(self):
        events = []
        language = ["en"]

        def set_language(lang):
            events.append("language")
            language[0] = lang

        i18n = types.SimpleNamespace(
            set_language=set_language, get_language=lambda: language[0],
            select_language=lambda: set_language("en"),
            tr=lambda sv, en: sv if language[0] == "sv" else en)

        def run_install(*args):
            events.append("install")
            return self.bin / "agents-opencode", None

        for args, expected in ((["--lang", "sv"], "Installerat:"),
                               (["--lang=en"], "Installed:"), ([], "Installed:")):
            with self.subTest(args=args):
                events.clear()
                output = io.StringIO()
                old_path = sys.path[:]
                try:
                    with mock.patch.dict(sys.modules, {"i18n": i18n}), \
                         mock.patch.object(installer, "install", side_effect=run_install), \
                         mock.patch.object(installer, "install_paths", return_value=(self.destination, self.bin)), \
                         contextlib.redirect_stdout(output):
                        self.assertEqual(installer.main(args), 0)
                finally:
                    sys.path[:] = old_path
                self.assertEqual(events, ["language", "install"])
                self.assertIn(expected, output.getvalue())
                self.assertIn(str(self.bin), output.getvalue())

    def test_windows_wrappers_check_version_forward_arguments_and_exit_status(self):
        for name, engine in (("install.cmd", '"%~dp0install.py"'),
                             ("agents-opencode.cmd", '"%ENGINE%"')):
            with self.subTest(name=name):
                text = (ROOT / name).read_text()
                self.assertIn("setlocal DisableDelayedExpansion", text)
                self.assertIn("sys.version_info >= (3, 10)", text)
                self.assertIn("py -3 -c", text)
                self.assertIn("python -c", text)
                for python in ("py -3", "python"):
                    self.assertIn(f"{python} {engine} %*\nexit /b %errorlevel%", text)
        text = (ROOT / "agents-opencode.cmd").read_text()
        self.assertIn(r"%~dp0lib\manager.py", text)
        self.assertIn(r"%LOCALAPPDATA%\agents-opencode\lib\manager.py", text)

    @unittest.skipIf(sys.platform == "win32", "Bash wrapper check runs on POSIX")
    def test_shell_wrapper_forwards_arguments_and_exit_status(self):
        # The stub installer only records its arguments; it cannot install anything.
        (self.source / "install.sh").write_bytes((ROOT / "install.sh").read_bytes())
        (self.source / "install.py").write_text(
            "import sys\nprint(repr(sys.argv[1:]))\nraise SystemExit(7)\n")
        args = ["--lang", "en", "space path å", "literal *"]
        result = subprocess.run(["bash", str(self.source / "install.sh"), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout.strip(), repr(args))

    @unittest.skipIf(sys.platform == "win32", "POSIX CLI; Windows layout is simulated separately")
    def test_cli_offline_install_language_and_installed_launcher(self):
        (self.source / "install.py").write_bytes((ROOT / "install.py").read_bytes())
        (self.source / "lib/i18n.py").write_bytes((ROOT / "lib/i18n.py").read_bytes())
        (self.source / "lib/manager.py").write_text(
            "import sys\nprint(repr(sys.argv[1:]))\nraise SystemExit(9)\n")
        env = {**os.environ, "HOME": str(self.root / "home"),
               "XDG_DATA_HOME": str(self.destination.parent), "XDG_BIN_HOME": str(self.bin)}
        for args, expected in (([], "Installed:"), (["--lang", "sv"], "Installerat:")):
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(self.source / "install.py"), *args],
                                        env=env, input="", capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
                self.assertNotIn("Select language", result.stdout)
                self.assertIn(str(self.bin), result.stdout)
        args = ["--lang", "sv", "status", "project space 日本語"]
        result = subprocess.run([str(self.bin / "agents-opencode"), *args], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertEqual(result.stdout.strip(), repr(args))
        self.assertFalse((self.root / "home").exists())


if __name__ == "__main__":
    unittest.main()
