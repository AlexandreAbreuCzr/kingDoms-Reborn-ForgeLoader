import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("kingdoms", Path(__file__).resolve().parents[1] / "scripts/kingdoms.py")
k = importlib.util.module_from_spec(spec)
spec.loader.exec_module(k)


class ProfileTests(unittest.TestCase):
    def test_preserves_unrelated_and_updates_duplicates_idempotently(self):
        original = "; comentario\r\n[Other]\r\nCulture=pt-BR\r\n[Target]\r\nValue=9\r\nValue=7\r\nOther=keep\r\n"
        changes = {"Target": {"Value": "2", "New": "1"}}
        changed = k.update_ini(original, changes)
        self.assertIn("; comentario\r\n[Other]\r\nCulture=pt-BR\r\n", changed)
        self.assertEqual(changed.count("Value=2"), 2)
        self.assertIn("Other=keep\r\n", changed)
        self.assertEqual(changed, k.update_ini(changed, changes))

    def test_encoding_and_no_final_newline(self):
        for encoding in ("utf-8-sig", "utf-16", "cp1252"):
            raw = "[Other]\r\nText=ação".encode(encoding)
            changed = k.edit_bytes(raw, {"Added": {"Key": "1"}})
            self.assertIn("Text=ação\r\n", changed.decode(encoding))

    @patch.object(k, "require_closed")
    def test_apply_restore_existing_and_originally_missing(self, _):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "saved/Config/WindowsNoEditor"
            config.mkdir(parents=True)
            original = b"[Internationalization]\r\nCulture=pt-BR\r\n"
            (config / "GameUserSettings.ini").write_bytes(original)
            plan = k.apply_profile(root / "saved")
            self.assertFalse(plan["applied"])
            self.assertFalse((config / "Engine.ini").exists())
            result = k.apply_profile(root / "saved", True, root / "backups")
            self.assertTrue(result["applied"])
            self.assertFalse(k.apply_profile(root / "saved", True, root / "backups")["applied"])
            k.restore_profile(result["backup"], root / "saved")
            self.assertEqual((config / "GameUserSettings.ini").read_bytes(), original)
            self.assertFalse((config / "Engine.ini").exists())

    @patch.object(k, "require_closed")
    def test_restore_refuses_new_user_changes_before_any_write(self, _):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = k.apply_profile(root / "saved", True, root / "backups")
            config = root / "saved/Config/WindowsNoEditor"
            before = (config / "GameUserSettings.ini").read_bytes()
            (config / "Engine.ini").write_text("[User]\nNew=1\n")
            with self.assertRaises(RuntimeError):
                k.restore_profile(result["backup"], root / "saved")
            self.assertEqual((config / "GameUserSettings.ini").read_bytes(), before)

    @patch.object(k, "running_game", return_value=[{"Id": 123}])
    def test_active_game_blocks_mutation(self, _):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                k.apply_profile(Path(directory), True, Path(directory) / "backups")


if __name__ == "__main__":
    unittest.main()
