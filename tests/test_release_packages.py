from pathlib import Path
import importlib.util
import json
import os
import re
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
    def test_ai_skill_and_local_references_survive_extraction(self):
        output = release_builder.build(devkit_only=True)
        config = json.loads((ROOT / 'release.json').read_text())
        with zipfile.ZipFile(output / config['devkit_archive']) as archive, tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive.extractall(root)
            self.assertTrue((root / 'AGENTS.md').is_file())
            guide = root / 'CRIAR-MOD-COM-IA.md'
            self.assertTrue(guide.is_file())
            skill = root / '.agents/skills/forgeloader-modding'
            self.assertTrue((skill / 'SKILL.md').is_file())
            self.assertTrue((skill / 'agents/openai.yaml').is_file())
            for markdown in skill.rglob('*.md'):
                for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', markdown.read_text(encoding='utf-8')):
                    if '://' in link or link.startswith('#'): continue
                    target = (markdown.parent / link.split('#', 1)[0]).resolve()
                    self.assertTrue(target.is_relative_to(skill.resolve()), f'Skill resource outside bundle: {link}')
                    self.assertTrue(target.is_file(), f'Missing bundled resource: {link}')
            result = subprocess.run([sys.executable, 'modkit/wizard.py'], input='4\n0\n',
                                    cwd=root, capture_output=True, text=True, encoding='utf-8',
                                    errors='replace', timeout=15, env={**os.environ, 'PYTHONUTF8': '1'})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(guide.read_text(encoding='utf-8'), result.stdout)
            self.assertFalse((root / 'MeusMods').exists(), 'Viewing AI instructions must not create or alter mod projects')

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
        self.assertTrue(patch['general_mod_loader'])
        self.assertFalse(patch['noasync_patch_applied'])
        self.assertLess(len(patch['append_hex']), 16384)
        self.assertTrue(all(0 <= row['offset'] < 4096 for row in patch['changes']))
        self.assertEqual(patch['target_sha256'], 'c676d4ac5533464cc2bbfefd6321c9a119d0f264069ddf265668f22d945d3df4')


if __name__ == '__main__': unittest.main()
