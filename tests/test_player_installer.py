"""Exercise the shipped PowerShell installer against temporary game copies."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell required')
class PlayerInstallerTests(unittest.TestCase):
    def prepare(self, root, original=b'MZ' + b'A' * 1022, target=None, dll=b'fake native module for tests'):
        if target is None: target = original[:10] + b'BB' + original[12:] + b'added import data'
        exe = root / 'game/PunCity/Binaries/Win64/PrototypeCity-Win64-Shipping.exe'
        exe.parent.mkdir(parents=True); exe.write_bytes(original)
        package = root / 'package'; (package / 'payload').mkdir(parents=True)
        shutil.copyfile(ROOT / 'installer/Setup-ForgeLoader.ps1', package / 'Setup-ForgeLoader.ps1')
        changes = []; at = 0
        # Header patch generator is separate; the installer applies verified intervals.
        for index in range(min(1024, len(original))):
            if original[index] != target[index]: changes.append({'offset': index, 'before': original[index:index+1].hex(), 'after': target[index:index+1].hex()})
        sha = lambda raw: hashlib.sha256(raw).hexdigest()
        patch = {'schema': 1, 'source_sha256': sha(original), 'target_sha256': sha(target),
                 'dll_sha256': sha(dll), 'source_length': len(original), 'target_length': len(target),
                 'changes': changes, 'append_hex': target[len(original):].hex()}
        (package / 'payload/player-patch.json').write_text(json.dumps(patch))
        (package / 'payload/KingdomsPortraits.dll').write_bytes(dll)
        saved = root / 'saved'; saved.mkdir(); (saved / 'PlayerInfo.dat').write_bytes(b'original profile')
        return exe, package, saved, target

    def invoke(self, root, package, saved, mode, success=True):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-File',
                                 str(package / 'Setup-ForgeLoader.ps1'), '-Mode', mode, '-NoUI',
                                 '-GamePath', str(root / 'game'), '-SavedPath', str(saved)],
                                capture_output=True, text=True, errors='replace', timeout=40)
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return json.loads(result.stdout) if success else result

    def test_install_idempotence_corrupt_backup_and_byte_exact_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); exe, package, saved, target = self.prepare(root)
            original = exe.read_bytes()
            result = self.invoke(root, package, saved, 'Install')
            self.assertEqual(exe.read_bytes(), target)
            self.assertEqual(self.invoke(root, package, saved, 'Install')['status'], 'already-installed')
            backup = Path(result['backup'])
            (backup / 'game.exe').write_bytes(b'corrupt')
            self.invoke(root, package, saved, 'Restore', False)
            self.assertEqual(exe.read_bytes(), target)
            (backup / 'game.exe').write_bytes(original)
            (saved / 'PlayerInfo.dat').write_bytes(b'new profile')
            self.invoke(root, package, saved, 'Restore')
            self.assertEqual(exe.read_bytes(), original)
            self.assertFalse((exe.parent / 'KingdomsPortraits.dll').exists())
            self.assertEqual((saved / 'PlayerInfo.dat').read_bytes(), b'original profile')
            self.assertEqual(next(backup.glob('BeforeRestore-*/PlayerInfo.dat')).read_bytes(), b'new profile')

    def test_wrong_build_and_corrupt_payload_refused_without_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); exe, package, saved, _ = self.prepare(root)
            exe.write_bytes(b'unknown build')
            self.invoke(root, package, saved, 'Install', False)
            self.assertEqual(exe.read_bytes(), b'unknown build')
            self.assertFalse((root / 'game/ForgeLoader').exists())
            (package / 'payload/KingdomsPortraits.dll').write_bytes(b'corrupt')
            self.invoke(root, package, saved, 'Install', False)
            self.assertFalse((root / 'game/ForgeLoader').exists())

    def test_known_runtime_upgrade_preserves_previous_dll_for_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);exe,package,saved,target=self.prepare(root)
            exe.write_bytes(target)
            old=b'previous trusted runtime';dll=exe.parent/'KingdomsPortraits.dll';dll.write_bytes(old)
            patch_path=package/'payload/player-patch.json';patch=json.loads(patch_path.read_text())
            patch['upgrade_from_dll_sha256']=[hashlib.sha256(old).hexdigest()];patch_path.write_text(json.dumps(patch))
            self.assertEqual(self.invoke(root,package,saved,'Install')['status'],'installed')
            self.assertNotEqual(dll.read_bytes(),old)
            self.invoke(root,package,saved,'Restore')
            self.assertEqual(dll.read_bytes(),old)
            self.assertEqual(exe.read_bytes(),target)

    @unittest.skipUnless((ROOT / '.local/original-image/PrototypeCity-Win64-Shipping.exe').exists(), 'Local original game fixture required')
    def test_real_release_patch_and_dll_restore_original(self):
        original = (ROOT / '.local/original-image/PrototypeCity-Win64-Shipping.exe').read_bytes()
        dll_path = ROOT / '.local/portrait-build/KingdomsPortraits.dll'
        if not dll_path.exists(): self.skipTest('Validated runtime fixture required')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); exe, package, saved, _ = self.prepare(root, original, original)
            shutil.copyfile(ROOT / 'profiles/player-patch.json', package / 'payload/player-patch.json')
            shutil.copyfile(dll_path, package / 'payload/KingdomsPortraits.dll')
            self.invoke(root, package, saved, 'Install')
            self.assertEqual(hashlib.sha256(exe.read_bytes()).hexdigest(), 'a5d2385660d9e819d2aa073cdd9c1d74c05149c9617f37cbb8b31e83708c4e24')
            self.invoke(root, package, saved, 'Restore')
            self.assertEqual(exe.read_bytes(), original)


if __name__ == '__main__': unittest.main()
