"""Installation must preserve the runtime required by folder builds."""
import os
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_launcher


class DesktopInstallTest(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows byte-range locking')
    def test_second_process_detects_owner_and_can_restart_after_release(self):
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory)
            owner=desktop_launcher.acquire_instance_lock(profile)
            self.assertIsNotNone(owner)
            script=("import sys; from pathlib import Path; "
                    "from desktop_launcher import acquire_instance_lock; "
                    "handle=acquire_instance_lock(Path(sys.argv[1])); "
                    "print('owned' if handle else 'busy'); "
                    "handle.close() if handle else None")
            def launch():
                return subprocess.run([sys.executable,'-c',script,directory],
                                      cwd=Path(desktop_launcher.__file__).parent,
                                      capture_output=True,text=True,check=True,timeout=15).stdout.strip()
            try:
                self.assertEqual(launch(),'busy')
            finally:owner.close()
            self.assertEqual(launch(),'owned')

    def test_existing_instance_falls_back_when_desktop_cannot_open(self):
        with patch.object(desktop_launcher,'open_desktop_window',side_effect=RuntimeError('Webview unavailable')), \
             patch.object(desktop_launcher.webbrowser,'open',return_value=True) as browser, \
             patch.object(desktop_launcher.logging,'exception'):
            desktop_launcher.reopen_instance('http://127.0.0.1:8765/')
        browser.assert_called_once_with('http://127.0.0.1:8765/')

    def test_existing_instance_keeps_desktop_when_available(self):
        with patch.object(desktop_launcher,'open_desktop_window') as desktop, \
             patch.object(desktop_launcher.webbrowser,'open') as browser:
            desktop_launcher.reopen_instance('http://127.0.0.1:8765/')
        desktop.assert_called_once_with('http://127.0.0.1:8765/')
        browser.assert_not_called()

    @unittest.skipUnless(os.name=='nt','Windows byte-range locking')
    def test_shortcut_launch_reopens_an_already_locked_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory)
            (profile/'instance.lock').write_bytes(b'0')
            (profile/'instance.json').write_text(json.dumps({'pid':123,'port':8765}),encoding='utf-8')
            owner=desktop_launcher.acquire_instance_lock(profile)
            self.assertIsNotNone(owner)
            try:
                with patch.object(sys,'argv',['Powder Ranger.exe','--data-dir',directory]), \
                     patch.object(desktop_launcher.http.client,'HTTPConnection') as connection, \
                     patch.object(desktop_launcher,'reopen_instance') as reopen, \
                     patch('local_app.Application',side_effect=AssertionError('Must reuse the running job')):
                    connection.return_value.getresponse.return_value.status=200
                    self.assertEqual(desktop_launcher.main(),0)
                reopen.assert_called_once_with('http://127.0.0.1:8765/',False)
                self.assertIsNone(desktop_launcher.acquire_instance_lock(profile))
            finally:owner.close()

    def test_copies_runtime_and_creates_shortcuts_after_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'download'
            runtime = source / '_internal'
            (runtime / 'PIL').mkdir(parents=True)
            (source / 'Powder Ranger.exe').write_bytes(b'executable')
            (runtime / 'python311.dll').write_bytes(b'python')
            (runtime / 'PIL' / 'imaging.pyd').write_bytes(b'imaging')
            target = root / 'profile' / 'Programs' / 'Powder Ranger'

            def shortcuts(*args, **kwargs):
                self.assertEqual((target / '_internal' / 'python311.dll').read_bytes(), b'python')
                self.assertEqual((target / '_internal' / 'PIL' / 'imaging.pyd').read_bytes(), b'imaging')
                self.assertEqual((target / 'Powder Ranger.exe').read_bytes(), b'executable')
                return type('Result', (), {'returncode': 0})()

            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', str(source / 'Powder Ranger.exe')), patch.dict(os.environ, {'LOCALAPPDATA': str(root / 'profile')}), patch.object(desktop_launcher.subprocess, 'run', side_effect=shortcuts):
                installed, notice = desktop_launcher.install_current_executable()
            self.assertEqual(installed, target / 'Powder Ranger.exe')
            self.assertIsNone(notice)

    def test_default_launch_uses_desktop_window(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_local_app = types.ModuleType('local_app')

            class FakeApplication:
                running = False

                def __init__(self, profile):
                    self.profile = profile

            class FakeServer:
                server_port = 8765

                def __init__(self, *args, **kwargs):
                    pass

                def serve_forever(self):
                    pass

                def shutdown(self):
                    pass

                def server_close(self):
                    pass

            fake_local_app.Application = FakeApplication
            fake_local_app.ThreadingHTTPServer = FakeServer
            fake_local_app.make_handler = lambda app: object()

            opened = []
            browser_launcher = []
            with patch.dict(sys.modules, {'local_app': fake_local_app}), patch.object(sys, 'argv', ['Powder Ranger.exe', '--data-dir', directory]), patch.object(desktop_launcher, 'open_desktop_window', side_effect=lambda url: opened.append(url)), patch.object(desktop_launcher, 'run_browser_launcher', side_effect=lambda *args: browser_launcher.append(args)):
                self.assertEqual(desktop_launcher.main(), 0)
            self.assertEqual(opened, ['http://127.0.0.1:8765/'])
            self.assertEqual(browser_launcher, [])

    def test_browser_flag_uses_fallback_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_local_app = types.ModuleType('local_app')

            class FakeApplication:
                running = False

                def __init__(self, profile):
                    self.profile = profile

            class FakeServer:
                server_port = 8766

                def __init__(self, *args, **kwargs):
                    pass

                def serve_forever(self):
                    pass

                def shutdown(self):
                    pass

                def server_close(self):
                    pass

            fake_local_app.Application = FakeApplication
            fake_local_app.ThreadingHTTPServer = FakeServer
            fake_local_app.make_handler = lambda app: object()

            opened = []
            browser_launcher = []
            with patch.dict(sys.modules, {'local_app': fake_local_app}), patch.object(sys, 'argv', ['Powder Ranger.exe', '--data-dir', directory, '--browser']), patch.object(desktop_launcher, 'open_desktop_window', side_effect=lambda url: opened.append(url)), patch.object(desktop_launcher, 'run_browser_launcher', side_effect=lambda *args: browser_launcher.append(args)):
                self.assertEqual(desktop_launcher.main(), 0)
            self.assertEqual(opened, [])
            self.assertEqual(len(browser_launcher), 1)


if __name__ == '__main__':
    unittest.main()
