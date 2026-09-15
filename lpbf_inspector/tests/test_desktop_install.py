"""Installation must preserve the runtime required by folder builds."""
import os
from pathlib import Path
import sys
import tempfile
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


if __name__ == '__main__':
    unittest.main()
