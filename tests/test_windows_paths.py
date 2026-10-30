"""Bounded path-policy checks; lexical Windows tests need no Windows host/share."""
import os
from pathlib import Path, PureWindowsPath
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from access_check import absolute_policy_path, is_filesystem_root, path_decision, validate


class WindowsLexicalTests(unittest.TestCase):
    def test_absolute_drive_and_unc_paths(self):
        for raw in ('C:\\work\\file', 'c:/work/file',
                    '\\\\server\\share\\folder', '//server/share/folder'):
            with self.subTest(path=raw):
                self.assertEqual(absolute_policy_path(raw, PureWindowsPath),
                                 PureWindowsPath(raw))
                self.assertFalse(is_filesystem_root(raw, PureWindowsPath))

    def test_ambiguous_and_relative_paths_rejected(self):
        for raw in ('C:foo', 'C:', '\\foo', '/foo', 'foo',
                    '\\\\server', '\\\\server\\', ''):
            with self.subTest(path=raw):
                with self.assertRaises(ValueError):
                    absolute_policy_path(raw, PureWindowsPath)

    def test_device_namespaces_rejected(self):
        for raw in ('\\\\?\\C:\\work', '\\\\.\\C:\\work',
                    '\\\\?\\UNC\\server\\share\\file',
                    '//?/C:/work', '//./PhysicalDrive0',
                    '\\??\\C:\\work', '\\\\??\\C:\\work',
                    '\\\\?\\GLOBALROOT\\Device\\HarddiskVolume1'):
            with self.subTest(path=raw):
                with self.assertRaises(ValueError):
                    absolute_policy_path(raw, PureWindowsPath)
                with self.assertRaises(ValueError):
                    is_filesystem_root(raw, PureWindowsPath)

    def test_drive_and_share_roots_including_dotdot(self):
        for raw in ('C:\\', 'c:/', 'C:/folder/..', 'C:/../../',
                    '\\\\server\\share', '\\\\server\\share\\',
                    '//server/share/folder/..'):
            with self.subTest(path=raw):
                self.assertTrue(is_filesystem_root(raw, PureWindowsPath))
        for raw in ('C:/folder', 'C:/folder/../other',
                    '//server/share/folder', '//server/share/../folder'):
            with self.subTest(path=raw):
                self.assertFalse(is_filesystem_root(raw, PureWindowsPath))


class NativePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / 'project'
        self.project.mkdir()
        self.policy = {
            'version': 1, 'project_root': str(self.project),
            'filesystem': {'default_outside': {'read': 'deny', 'write': 'deny'},
                           'paths': []},
            'network': {'default': 'deny', 'hosts': []},
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_native_containment_and_defaults(self):
        validate(self.policy)
        for target, expected in ((self.project / 'new/file', 'allow'),
                                 (self.base / 'project-other/file', 'deny'),
                                 (self.project / '../outside', 'deny')):
            self.assertEqual(path_decision(self.policy, target, 'read'), expected)
        self.policy['filesystem']['default_outside']['read'] = 'allow'
        self.assertEqual(path_decision(self.policy, self.base / 'outside', 'read'), 'allow')

    def test_native_nested_rules_and_canonical_paths(self):
        share = self.base / 'share'
        self.policy['filesystem']['paths'] = [
            {'path': str(share), 'read': 'allow', 'write': 'deny'},
            {'path': str(share / 'private'), 'read': 'deny', 'write': 'deny'},
        ]
        validate(self.policy)
        for target, expected in ((share / 'public/file', 'allow'),
                                 (share / 'private/file', 'deny'),
                                 (share / 'public/../private/file', 'deny'),
                                 (self.base / 'share-other/file', 'deny')):
            self.assertEqual(path_decision(self.policy, target, 'read'), expected)

    def test_root_allow_rejected_but_root_deny_or_ask_allowed(self):
        root = self.project.anchor
        self.assertTrue(is_filesystem_root(root))
        for read, write in (('allow', 'deny'), ('deny', 'allow')):
            self.policy['filesystem']['paths'] = [
                {'path': root, 'read': read, 'write': write}]
            with self.assertRaises(ValueError):
                validate(self.policy)
        for action in ('deny', 'ask'):
            self.policy['filesystem']['paths'] = [
                {'path': root, 'read': action, 'write': action}]
            validate(self.policy)

    def test_project_root_must_be_absolute_and_not_filesystem_root(self):
        for root in ('relative-project', self.project.anchor,
                     str(Path(self.project.anchor) / 'folder' / '..')):
            self.policy['project_root'] = root
            with self.assertRaises(ValueError):
                validate(self.policy)
            with self.assertRaises(ValueError):
                path_decision(self.policy, self.project / 'file', 'read')

    def test_symlinks_resolve_before_containment_and_root_validation(self):
        link = self.project / 'escape'
        root_link = self.base / 'root-link'
        try:
            link.symlink_to(self.base, target_is_directory=True)
            root_link.symlink_to(self.project.anchor, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest('Symlink creation unavailable: '+str(exc))
        self.assertEqual(path_decision(self.policy, link / 'outside', 'read'), 'deny')
        self.assertTrue(is_filesystem_root(root_link))
        self.policy['filesystem']['paths'] = [
            {'path': str(root_link), 'read': 'allow', 'write': 'deny'}]
        with self.assertRaises(ValueError):
            validate(self.policy)
        self.policy['filesystem']['paths'] = []
        self.policy['project_root'] = str(root_link)
        with self.assertRaises(ValueError):
            validate(self.policy)

    @unittest.skipUnless(os.name == 'posix', 'POSIX host semantics')
    def test_posix_names_and_relative_requests_unchanged(self):
        name = self.project / 'C:foo\\bar'
        self.assertEqual(absolute_policy_path(name), name)
        self.assertEqual(path_decision(self.policy, name, 'read'), 'allow')
        relative = self.project.relative_to(Path.cwd()) / 'file'
        self.assertEqual(path_decision(self.policy, relative, 'read'), 'allow')

    @unittest.skipUnless(os.name == 'nt', 'Windows native path semantics')
    def test_windows_case_and_different_drive(self):
        self.assertEqual(path_decision(self.policy, str(self.project).swapcase() + '\\file',
                                       'read'), 'allow')
        other = 'Z' if self.project.drive[0].upper() != 'Z' else 'Y'
        self.assertEqual(path_decision(self.policy, other + ':\\outside\\file', 'read'), 'deny')

    @unittest.skipUnless(os.name == 'nt', 'Windows native path semantics')
    def test_windows_native_invalid_policy_and_request_paths(self):
        for raw in ('C:foo', '\\foo', '\\\\?\\C:\\work', '\\\\.\\C:\\work'):
            with self.subTest(path=raw):
                with self.assertRaises(ValueError):
                    path_decision(self.policy, raw, 'read')
                self.policy['filesystem']['paths'] = [
                    {'path': raw, 'read': 'deny', 'write': 'deny'}]
                with self.assertRaises(ValueError):
                    validate(self.policy)


if __name__ == '__main__':
    unittest.main()
