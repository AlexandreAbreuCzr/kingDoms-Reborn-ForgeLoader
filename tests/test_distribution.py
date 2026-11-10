from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_portable", ROOT / "scripts/build_portable.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DistributionTests(unittest.TestCase):
    def test_allowlist_and_member_digests(self):
        archive_path = builder.build()
        with zipfile.ZipFile(archive_path) as archive:
            prefix = "KingdomsReborn-Toolkit/"
            expected = {prefix + n for n in builder.FILES} | {prefix + "manifest-sha256.json"}
            self.assertEqual(set(archive.namelist()), expected)
            manifest = json.loads(archive.read(prefix + "manifest-sha256.json"))
            for name, checksum in manifest.items():
                self.assertEqual(hashlib.sha256(archive.read(prefix + name)).hexdigest(), checksum)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell required")
    def test_extracted_package_defaults_apply_restore(self):
        archive_path = builder.build()
        with tempfile.TemporaryDirectory(prefix="kingdoms package ") as directory:
            root = Path(directory)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(root)
            package = root / "KingdomsReborn-Toolkit"
            saved = root / "saved"
            command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
                       str(package / "KingdomsToolkit.ps1"), "-SavedPath", str(saved)]
            for mode in ("Apply", "Restore"):
                result = subprocess.run(command + ["-Mode", mode], capture_output=True, text=True,
                                        errors="replace", timeout=25)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                if mode == "Apply":
                    self.assertTrue((saved / "Config/WindowsNoEditor/Engine.ini").is_file())
                    self.assertTrue(list((package / "Dados").glob("backup-*/manifest.json")))
            self.assertFalse((saved / "Config/WindowsNoEditor/Engine.ini").exists())


if __name__ == "__main__":
    unittest.main()
