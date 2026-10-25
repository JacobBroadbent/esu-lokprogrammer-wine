import importlib.util
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('setup_tool', Path(__file__).parents[1] / 'scripts/lokprogrammer.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class SetupGuards(unittest.TestCase):
    def test_nonempty_prefix_is_not_initialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            (prefix / 'important').write_text('keep')
            with patch.object(tool, 'wine') as invoke:
                with self.assertRaisesRegex(RuntimeError, 'nonempty'):
                    tool.init_prefix(SimpleNamespace(prefix=prefix))
                invoke.assert_not_called()
                self.assertEqual((prefix / 'important').read_text(), 'keep')

    def test_wrong_prefix_architecture_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            (prefix / 'system.reg').write_text('WINE REGISTRY Version 2\n#arch=win64\n')
            with self.assertRaisesRegex(RuntimeError, 'win32'):
                tool.require_prefix(SimpleNamespace(prefix=prefix))

    def test_mapping_conflict_does_not_remove_existing_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / 'first', root / 'second'
            first.mkdir(); second.mkdir()
            link = root / 'drive'
            link.symlink_to(first, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, 'retained'):
                tool.set_link(link, second)
            self.assertEqual(link.resolve(), first)
            tool.set_link(link, second, replace=True)
            self.assertEqual(link.resolve(), second)

    def test_stable_device_alias_is_kept_in_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            device = root / 'ttyUSB0'
            device.write_text('')
            stable = root / 'usb-FTDI-stable-id'
            stable.symlink_to(device)
            link = root / 'com1'
            tool.set_link(link, stable)
            import os
            self.assertEqual(os.readlink(link), str(stable))
            tool.set_link(link, stable)  # Repeating the same stable mapping is safe.

    def test_regular_file_never_replaced_by_drive_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            link = root / 'drive'
            link.write_text('keep')
            with self.assertRaises(RuntimeError):
                tool.set_link(link, root, replace=True)
            self.assertEqual(link.read_text(), 'keep')

    def test_raw_tty_path_rejected_before_mapping(self):
        with patch.object(tool, 'require_prefix'), patch.object(tool, 'require_closed'), patch.object(tool, 'set_link') as link:
            with self.assertRaisesRegex(RuntimeError, 'by-id'):
                tool.map_port(SimpleNamespace(device=Path('/dev/ttyUSB0'), prefix=Path('/unused'), replace=False))
            link.assert_not_called()

    def test_running_app_blocks_helper_install(self):
        output = SimpleNamespace(stdout='"LokProgrammerWineCompat.exe","32","Console","1","100 K"\n')
        with patch.object(tool, 'wine', return_value=output):
            with self.assertRaisesRegex(RuntimeError, 'close LokProgrammer'):
                tool.require_closed(SimpleNamespace())

    def test_download_hash_mismatch_never_becomes_cached_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'untrusted'
            source.write_bytes(b'incorrect package')
            item = {'url': source.as_uri(), 'sha256': '0' * 64}
            with patch.object(tool, 'ROOT', root), patch.dict(tool.LOCK, {'example': item}):
                with self.assertRaisesRegex(RuntimeError, 'SHA-256 mismatch'):
                    tool.download('example')
            self.assertFalse((root / '.cache/untrusted').exists())
            self.assertFalse((root / '.cache/untrusted.partial').exists())


if __name__ == '__main__':
    unittest.main()
