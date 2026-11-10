"""Check the shipped patch against the exact supplied binary in temporary folders."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home() / "Downloads/Kingdoms Reborn/PunCity/Binaries/Win64/PrototypeCity-Win64-Shipping.exe"
cached = ROOT / '.local/original-image/PrototypeCity-Win64-Shipping.exe'
if cached.exists(): SOURCE = cached
if os.environ.get('KINGDOMS_ORIGINAL_EXE'): SOURCE = Path(os.environ['KINGDOMS_ORIGINAL_EXE'])
SPEC = json.loads((ROOT / "profiles/noasync-binary-patch.json").read_text())


@unittest.skipUnless(os.name == "nt", "Windows PowerShell required")
class BinaryPatchTests(unittest.TestCase):
    def prepare(self, root):
        script = root / "tool/KingdomsToolkit.ps1"
        script.parent.mkdir()
        shutil.copyfile(ROOT / "portable/KingdomsToolkit.ps1", script)
        shutil.copyfile(ROOT / "profiles/noasync-binary-patch.json", script.parent / "noasync-binary-patch.json")
        target = root / "game" / SPEC["target_relative_path"]
        target.parent.mkdir(parents=True)
        (root / "game/KingdomsReborn.exe").write_bytes(b"not executed in this test")
        return script, target

    def run_mode(self, root, script, mode, expected=0):
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script),
                                 "-Mode", mode, "-GamePath", str(root / "game"), "-DataPath", str(root / "data")],
                                capture_output=True, text=True, errors="replace", timeout=40)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)

    @unittest.skipUnless(SOURCE.exists() and hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SPEC['source_sha256'], "Exact original game fixture required")
    def test_exact_four_byte_patch_idempotence_and_byte_exact_restore(self):
        raw = SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), SPEC["source_sha256"])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script, target = self.prepare(root)
            shutil.copyfile(SOURCE, target)
            self.run_mode(root, script, "PatchAsync")
            patched = target.read_bytes()
            self.assertEqual(hashlib.sha256(patched).hexdigest(), SPEC["patched_sha256"])
            offset = SPEC["file_offset"]
            self.assertEqual(patched[:offset], raw[:offset])
            self.assertEqual(patched[offset:offset+4], bytes.fromhex("33c0c390"))
            self.assertEqual(patched[offset+4:], raw[offset+4:])
            self.run_mode(root, script, "PatchAsync")
            self.assertEqual(len(list((root / "data").glob("binary-backup-*"))), 1)
            backup = next((root / "data").glob("binary-backup-*/PrototypeCity-Win64-Shipping.exe"))
            backup.write_bytes(b"corrupted backup")
            self.run_mode(root, script, "RestorePatch", expected=1)
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), SPEC["patched_sha256"])
            shutil.copyfile(SOURCE, backup)
            self.run_mode(root, script, "RestorePatch")
            self.assertEqual(target.read_bytes(), raw)

    def test_different_build_refused_without_write_or_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            script, target = self.prepare(root)
            raw = b"unknown game version"
            target.write_bytes(raw)
            self.run_mode(root, script, "PatchAsync", expected=1)
            self.assertEqual(target.read_bytes(), raw)
            self.assertFalse(list((root / "data").glob("binary-backup-*")))


if __name__ == "__main__":
    unittest.main()
