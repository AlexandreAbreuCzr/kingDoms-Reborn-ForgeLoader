"""Exercise the actual Windows PowerShell 5.1 entry point on temporary configs."""
from pathlib import Path
import json
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "nt", "Windows PowerShell required")
class PortableTests(unittest.TestCase):
    def invoke(self, mode, root, success=True):
        result = subprocess.run([
            "powershell.exe", "-NoProfile", "-NonInteractive", "-File",
            str(ROOT / "portable/KingdomsToolkit.ps1"), "-Mode", mode,
            "-SavedPath", str(root / "saved"), "-DataPath", str(root / "Dados"),
            "-ProfilePath", str(ROOT / "profiles/startup-safe.json"),
        ], capture_output=True, text=True, errors="replace", timeout=25)
        self.assertEqual(result.returncode, 0 if success else 1, result.stdout + result.stderr)
        return result

    def test_apply_idempotence_and_restore_after_game_rewrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "saved/Config/WindowsNoEditor"
            config.mkdir(parents=True)
            original = b"; keep\r\n[Internationalization]\r\nCulture=pt-BR\r\n[/Script/Engine.GameUserSettings]\r\nFrameRateLimit=0\r\nFrameRateLimit=60\r\n[Other]\r\nCustom=yes\r\n"
            path = config / "GameUserSettings.ini"
            path.write_bytes(original)
            self.invoke("Apply", root)
            changed = path.read_bytes()
            self.assertIn(b"Culture=pt-BR\r\n", changed)
            self.assertIn(b"[Other]\r\nCustom=yes\r\n", changed)
            self.assertEqual(changed.count(b"FrameRateLimit=45.000000"), 2)
            self.invoke("Apply", root)
            self.assertEqual(path.read_bytes(), changed)
            self.assertEqual(len(list((root / "Dados").glob("backup-*"))), 1)
            path.write_bytes(changed + b"[GameRewrite]\r\nKeep=1\r\n")
            self.invoke("Restore", root)
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse((config / "Engine.ini").exists())
            safety = list((root / "Dados").glob("antes-de-restaurar-*"))
            self.assertIn(b"GameRewrite", (safety[0] / path.name).read_bytes())

    def test_duplicate_sections_refused_without_modification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "saved/Config/WindowsNoEditor"
            config.mkdir(parents=True)
            path = config / "Engine.ini"
            original = b"[SystemSettings]\nX=1\n[SystemSettings]\nX=2\n"
            path.write_bytes(original)
            self.invoke("Apply", root, success=False)
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse((config / "GameUserSettings.ini").exists())

    def test_corrupt_backup_refused_before_restoring_any_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "saved/Config/WindowsNoEditor"
            config.mkdir(parents=True)
            (config / "Engine.ini").write_bytes(b"[Core.System]\nPath=keep\n")
            self.invoke("Apply", root)
            before = {p.name: p.read_bytes() for p in config.iterdir()}
            backup = next((root / "Dados").glob("backup-*"))
            (backup / "Engine.ini").write_bytes(b"corrupt")
            self.invoke("Restore", root, success=False)
            self.assertEqual(before, {p.name: p.read_bytes() for p in config.iterdir()})

    def test_unicode_bom_preserved(self):
        for encoding in ("utf-8-sig", "utf-16"):
            with self.subTest(encoding=encoding), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config = root / "saved/Config/WindowsNoEditor"
                config.mkdir(parents=True)
                path = config / "Engine.ini"
                original = "[Other]\r\nText=ação\r\n".encode(encoding)
                path.write_bytes(original)
                self.invoke("Apply", root)
                self.assertIn("Text=ação\r\n", path.read_bytes().decode(encoding))
                self.invoke("Restore", root)
                self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
