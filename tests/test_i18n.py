"""Language selection, explicit UI translations, and portable launch contracts."""
import ast
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import string
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

MANAGER = Path(__file__).resolve().parents[1] / 'lib' / 'manager.py'
spec = importlib.util.spec_from_file_location('manager_i18n_test', MANAGER)
mgr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mgr)
import i18n

PERM = dict(shell='allow', gitpush='deny', internet='deny', outside_read='deny',
            outside_write='deny', sudo='deny', destructive='deny', secrets='deny',
            unattended=False, mounts=[])


class LanguageTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language('en')

    def test_shared_language_and_explicit_translation(self):
        for lang, expected in [('sv', 'Hej {name}'), ('en', 'Hello {name}')]:
            self.assertEqual(i18n.set_language(lang), lang)
            self.assertEqual(mgr.get_language(), lang)
            self.assertEqual(i18n.tr('Hej {name}', 'Hello {name}'), expected)
        with self.assertRaises(ValueError):
            i18n.set_language('de')
        self.assertEqual(i18n.get_language(), 'en')

    def test_selector_interactive_and_repeated_each_startup(self):
        output = io.StringIO()
        with patch('sys.stdin.isatty', return_value=True), contextlib.redirect_stdout(output), \
                patch('builtins.input', side_effect=['bad', '1', '2']):
            self.assertEqual(i18n.select_language(), 'sv')
            self.assertEqual(i18n.select_language(), 'en')
        self.assertEqual(output.getvalue().count('Välj språk / Select language:'), 2)
        self.assertIn('Svenska', output.getvalue())
        self.assertIn('English', output.getvalue())

    def test_noninteractive_and_explicit_never_prompt(self):
        with patch('sys.stdin.isatty', return_value=False), \
                patch('builtins.input', side_effect=AssertionError('unexpected input')):
            i18n.set_language('sv')
            self.assertEqual(i18n.select_language(), 'en')
            self.assertEqual(i18n.select_language('sv'), 'sv')

    def test_language_is_first_interactive_manager_output(self):
        output = io.StringIO()
        with patch('sys.stdin.isatty', return_value=True), \
                patch('builtins.input', side_effect=['1', '0']), contextlib.redirect_stdout(output):
            mgr.main([])
        text = output.getvalue()
        self.assertTrue(text.startswith('Välj språk / Select language:'))
        self.assertIn('Avsluta', text)
        self.assertNotIn(' 0) Exit', text)

    def test_lang_anywhere(self):
        for args in [ ['--lang', 'sv', 'status', '.'], ['status', '--lang', 'sv', '.'],
                      ['status', '.', '--lang', 'sv'], ['status', '.', '--lang=en'] ]:
            with self.subTest(args=args), patch('builtins.input', side_effect=AssertionError('prompt')), \
                    patch.object(mgr, 'status') as status:
                mgr.main(args)
                status.assert_called_once_with(Path.cwd().resolve())
                self.assertEqual(i18n.get_language(), 'en' if args[-1]=='--lang=en' else 'sv')

    def test_help_version_no_prompt_even_on_tty(self):
        for args in [['--help'], ['--version'], ['install', '--help'], ['--lang', 'sv', '--help']]:
            with self.subTest(args=args), patch('sys.stdin.isatty', return_value=True), \
                    patch('builtins.input', side_effect=AssertionError('prompt')), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(mgr.main(args), 0)
                if '--help' in args:
                    self.assertIn('Ingen modell' if 'sv' in args else 'No model', output.getvalue())

    def test_cli_noninteractive_defaults_english(self):
        result = subprocess.run([sys.executable, str(MANAGER), 'status'],
                                input='', text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('Select language', result.stdout)
        # The development repo may itself have a manifest.
        self.assertTrue('Project:' in result.stdout or 'No v2 manifest' in result.stdout)

    def test_cli_invalid_language_and_unknown_command(self):
        for args in [['--lang', 'xx'], ['--lang'], ['--lang', 'en', 'unknown']]:
            with self.subTest(args=args):
                result = subprocess.run([sys.executable, str(MANAGER), *args],
                                        input='', text=True, capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('Traceback', result.stderr)
                self.assertNotIn('Select language:', result.stdout)

    def test_confirm_translated_and_accepts_both_languages(self):
        for lang, answer, hint in [('sv', 'ja', 'j/N'), ('en', 'yes', 'y/N')]:
            i18n.set_language(lang)
            with patch('builtins.input', return_value=answer) as inp:
                self.assertTrue(mgr.confirm('test'))
                self.assertIn(hint, inp.call_args.args[0])

    def test_all_explicit_translation_placeholders_match(self):
        tree = ast.parse(MANAGER.read_text(encoding='utf-8'))
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr':
                self.assertEqual(len(node.args), 2)
                sv, en = [ast.literal_eval(arg) for arg in node.args]
                fields = lambda text: sorted(field for _, field, _, _ in string.Formatter().parse(text) if field is not None)
                self.assertEqual(fields(sv), fields(en), (sv, en))
                self.assertTrue(sv)
                self.assertTrue(en)
                count += 1
        self.assertGreater(count, 150)

    def test_swedish_ui_literals_are_explicit_translations(self):
        tree = ast.parse(MANAGER.read_text(encoding='utf-8'))
        translated = {id(arg) for node in ast.walk(tree) if isinstance(node, ast.Call)
                      and isinstance(node.func, ast.Name) and node.func.id == 'tr' for arg in node.args}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and any(c in node.value for c in 'åäöÅÄÖ'):
                # Invalid --lang diagnostics deliberately remain bilingual.
                if node.value.startswith('--lang requires'): continue
                self.assertIn(id(node), translated, (node.lineno, node.value))

    def test_generation_is_language_independent(self):
        results = []
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for lang in ('sv', 'en'):
                i18n.set_language(lang)
                with contextlib.redirect_stdout(io.StringIO()):
                    mgr.apply(project, ['software-engineer'], {'software-engineer': 'test/model'}, PERM, 'SHAREABLE')
                results.append({str(p.relative_to(project)): p.read_bytes()
                                for p in project.rglob('*') if p.is_file() and '.backup-' not in p.name})
        self.assertEqual(results[0], results[1])
        self.assertIn(b'Project policy', results[0]['PROJECT_POLICY.md'])

    def test_wizards_in_both_languages_keep_policy_values_english(self):
        for lang in ('sv', 'en'):
            with self.subTest(lang=lang):
                i18n.set_language(lang)
                with patch('builtins.input', side_effect=['1'] + [''] * 12 + ['n', 'n', 'y']) as inp, \
                        contextlib.redirect_stdout(io.StringIO()) as output:
                    permission = mgr.permission_wizard()
                self.assertEqual(permission['shell'], 'ask')
                self.assertFalse(permission['unattended'])
                self.assertIn('Behörighetsguide' if lang=='sv' else 'Permission wizard', output.getvalue())
                self.assertIn('Shellkommandon' if lang=='sv' else 'Shell commands', inp.call_args_list[1].args[0])
                access = mgr.default_access_policy(Path.cwd(), permission)
                with patch('builtins.input', side_effect=['n'] * 4 + ['y']), \
                        contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(mgr.access_wizard(Path.cwd(), access), access)
                self.assertIn('Åtkomstpolicy' if lang=='sv' else 'Access policy', output.getvalue())
                with patch('builtins.input', side_effect=['1', 'n']), \
                        contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(RuntimeError, 'Avbrutet' if lang=='sv' else 'Cancelled'):
                        mgr.choose_mode()

    def test_mounts_reject_relative_then_accept_absolute(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(mgr, 'prompt', side_effect=['relative/share', 'C:foo', directory, '']), \
                    patch.object(mgr, 'absolute_policy_path', wraps=mgr.absolute_policy_path) as absolute, \
                    patch.object(mgr, 'policy_action', side_effect=['allow', 'deny']) as action, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                mounts = mgr.ask_mounts()
            self.assertEqual(mounts, [{'path': str(Path(directory).resolve()), 'read': 'allow', 'write': 'deny'}])
            self.assertEqual([call.args[0] for call in absolute.call_args_list], ['relative/share', 'C:foo', directory])
            self.assertEqual(action.call_count, 2)
            self.assertEqual(output.getvalue().count('Enter an absolute path without device namespaces.'), 2)

    def test_access_rejects_relative_then_accepts_absolute(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            access = mgr.default_access_policy(project, PERM)
            allowed = str(project / 'allowed')
            with patch.object(mgr, 'prompt', side_effect=['relative/path', 'C:foo', allowed, '']), \
                    patch.object(mgr, 'confirm', side_effect=[False, True, False, False, False, True]), \
                    patch.object(mgr, 'choose', return_value='1') as choose, \
                    patch.object(mgr, 'policy_action', side_effect=['allow', 'deny']), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                result = mgr.access_wizard(project, access)
            self.assertEqual(result['filesystem']['paths'], [dict(path=allowed, kind='local', read='allow', write='deny')])
            choose.assert_called_once()
            self.assertEqual(output.getvalue().count('Enter an absolute path without device namespaces.'), 2)

    def test_path_helper_errors_are_localized_and_blank_finishes(self):
        for lang in ('sv', 'en'):
            for wizard in ('mounts', 'access'):
                with self.subTest(lang=lang, wizard=wizard):
                    i18n.set_language(lang)
                    with patch.object(mgr, 'prompt', side_effect=['\\\\?\\C:\\device', '']), \
                            patch.object(mgr, 'absolute_policy_path', side_effect=ValueError('internal helper diagnostic')) as absolute, \
                            patch.object(mgr, 'confirm', side_effect=[False, True, False, False, True]), \
                            contextlib.redirect_stdout(io.StringIO()) as output:
                        if wizard == 'mounts':
                            self.assertEqual(mgr.ask_mounts(), [])
                        else:
                            access = mgr.default_access_policy(Path.cwd(), PERM)
                            self.assertEqual(mgr.access_wizard(Path.cwd(), access), access)
                    absolute.assert_called_once_with('\\\\?\\C:\\device')
                    self.assertIn('Ange en absolut sökväg utan enhetsnamnrymder.' if lang=='sv' else
                                  'Enter an absolute path without device namespaces.', output.getvalue())
                    self.assertNotIn('internal helper diagnostic', output.getvalue())


class PortableLaunchTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language('en')

    def test_resolves_actual_binary_and_models(self):
        with patch.object(mgr.shutil, 'which', return_value='/path with spaces/opencode'):
            self.assertEqual(mgr.opencode_command(['models'], windows=False), ['/path with spaces/opencode', 'models'])
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(mgr.shutil, 'which', return_value='/actual/opencode'), \
                patch.object(mgr.subprocess, 'run', return_value=Mock(returncode=0, stdout='provider/model\n')) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mgr.list_models(Path('.')), ['provider/model'])
            self.assertEqual(run.call_args.args[0], ['/actual/opencode', 'models'])
            self.assertEqual(run.call_args.kwargs['cwd'], Path('.'))

    def test_windows_exe_and_batch_shims(self):
        for suffix in ('.cmd', '.bat', '.CMD'):
            path = 'C:\\Program Files\\OpenCode\\opencode' + suffix
            with patch.object(mgr.shutil, 'which', return_value='C:\\Windows\\System32\\cmd.exe'):
                cmd = mgr.opencode_command(['--continue', '--auto'], executable=path, windows=True)
            self.assertEqual(cmd, 'C:\\Windows\\System32\\cmd.exe /d /s /c ""' + path + '" --continue --auto"')
        path = 'C:\\Program Files\\OpenCode\\opencode.exe'
        self.assertEqual(mgr.opencode_command(['models'], executable=path, windows=True), [path, 'models'])

    def test_batch_rejects_interpolation_and_arbitrary_args(self):
        for unsafe in ['C:\\a%TEMP%\\opencode.cmd', 'C:\\a&b\\opencode.bat', 'C:\\a!x!\\opencode.cmd', 'bad".cmd']:
            with self.subTest(unsafe=unsafe), self.assertRaises(RuntimeError):
                mgr.opencode_command(executable=unsafe, windows=True)
        for argument in ['a & whoami', 'C:\\project path', '--model', 'models\nwhoami']:
            with self.subTest(argument=argument), self.assertRaises(ValueError):
                mgr.opencode_command([argument], executable='opencode.cmd', windows=True)

    def test_cwd_and_exit_status_propagation(self):
        project = Path('project with spaces & special chars')
        before = Path.cwd()
        with patch.object(mgr, 'read_manifest', return_value={'permissions': {'unattended': True}}), \
                patch.object(mgr, 'opencode_command', return_value=['/actual/opencode', '--continue', '--auto']) as cmd, \
                patch.object(mgr.subprocess, 'run', return_value=Mock(returncode=23)) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mgr.run_opencode(project, resume=True), 23)
            cmd.assert_called_once_with(['--continue', '--auto'])
            run.assert_called_once_with(['/actual/opencode', '--continue', '--auto'], cwd=project)
        self.assertEqual(Path.cwd(), before)
        with patch.object(mgr, 'run_opencode', return_value=23):
            self.assertEqual(mgr.main(['--lang', 'en', 'run', '.']), 23)
            self.assertEqual(mgr.main(['resume', '.', '--lang', 'en']), 23)
        with patch.object(mgr, 'run_opencode', return_value=23), \
                patch.object(mgr, 'project_dir', return_value=project), \
                patch('builtins.input', return_value='7'), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mgr.menu(), 23)

    def test_windows_permission_path_spellings(self):
        access = mgr.default_access_policy('C:\\Work Area\\project', PERM)
        access['filesystem']['paths'] = [dict(path='D:\\data', read='allow', write='deny')]
        permission = mgr.make_permission(PERM, access)
        for pattern in ['*:/*', '*:\\*', '\\\\*']:
            self.assertEqual(permission['read'][pattern], 'deny')
        for pattern in ['C:\\Work Area\\project\\**', 'C:/Work Area/project/**', 'D:\\data\\**', 'D:/data/**']:
            self.assertEqual(permission['read'][pattern], 'allow')
        for pattern in ['C:/Work Area/project/AGENT_ACCESS_POLICY.json', 'C:\\Work Area\\project\\AGENT_ACCESS_POLICY.json']:
            self.assertEqual(permission['edit'][pattern], 'deny')

    def test_windows_helper_instructions_stay_english(self):
        access = mgr.default_access_policy('C:/work/project', PERM)
        i18n.set_language('sv')
        with patch.object(mgr.os, 'name', 'nt'):
            text = mgr.render_access_rules(access)
            permission = mgr.make_permission(PERM, {**access, 'network': {
                'default': 'deny', 'hosts': [{'host': 'example.org', 'access': 'allow'}]}})
        self.assertIn('`python .opencode/tools/access_check.py path read C:/absolute/path`', text)
        self.assertNotIn('`python3 ', text)
        self.assertIn('PowerShell, cmd.exe, batch shims', text)
        self.assertEqual(permission['bash']['python .opencode/tools/access_fetch.py *'], 'allow')


if __name__ == '__main__':
    unittest.main()
