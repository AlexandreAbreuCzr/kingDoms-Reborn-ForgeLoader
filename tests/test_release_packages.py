from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_builder', ROOT / 'scripts/build_releases.py')
release_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release_builder)


class ReleasePackageTests(unittest.TestCase):
    def test_devkit_extracts_and_menu_creates_a_valid_project(self):
        output = release_builder.build(devkit_only=True)
        config = json.loads((ROOT / 'release.json').read_text())
        with zipfile.ZipFile(output / config['devkit_archive']) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn('Abrir-DevKit.cmd', archive.namelist())
            self.assertFalse(any(name.lower().endswith(('.exe', '.dll', '.pdb', '.dmp', '.pak')) for name in archive.namelist()))
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder); archive.extractall(root)
                result = subprocess.run([sys.executable, str(root / 'modkit/wizard.py')],
                                        input='1\ntest.package\nMeu Mod\nn\n0\n', capture_output=True,
                                        text=True, errors='replace', timeout=15, cwd=root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertTrue((root / 'MeusMods/test.package/Scripts/main.lua').exists())
                result = subprocess.run([sys.executable, 'modkit/krmodkit.py', 'validate', 'MeusMods'],
                                        cwd=root, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_small_patch_contains_no_texture_or_game_code_changes(self):
        patch = json.loads((ROOT / 'profiles/player-patch.json').read_text())
        self.assertFalse(patch['general_mod_loader'])
        self.assertFalse(patch['noasync_patch_applied'])
        self.assertLess(len(patch['append_hex']), 16384)
        self.assertTrue(all(0 <= row['offset'] < 4096 for row in patch['changes']))
        self.assertEqual(patch['target_sha256'], 'a5d2385660d9e819d2aa073cdd9c1d74c05149c9617f37cbb8b31e83708c4e24')


if __name__ == '__main__': unittest.main()
