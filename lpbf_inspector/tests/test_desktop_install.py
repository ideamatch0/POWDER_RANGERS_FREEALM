"""Installation must preserve the runtime required by folder builds."""
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_launcher


class DesktopInstallTest(unittest.TestCase):
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
