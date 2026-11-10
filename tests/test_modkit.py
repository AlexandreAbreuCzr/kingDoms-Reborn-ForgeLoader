import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('krmodkit', ROOT / 'modkit/krmodkit.py')
kit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kit)


class ModKitTests(unittest.TestCase):
    def mod(self, root, ident, required=False):
        folder = root / ident
        kit.new_mod(folder, ident, ident, required)
        return folder

    def profile(self):
        return {'schema': 1, 'api_major': 1, 'adapter': 'test', 'game_sha256': 'a' * 64,
                'shared_mods': [{'id': 'core.shared_portraits', 'version': '3.0.0', 'package_sha256': 'b' * 64}],
                'local_mods': []}

    def test_template_roundtrip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = self.mod(root, 'test.hello')
            self.assertEqual(kit.load_order(kit.discover(root)), ['test.hello'])
            with self.assertRaises(kit.ModError):
                kit.new_mod(path, 'test.hello', 'Overwritten')
            self.assertEqual(kit.read_json(path / 'mod.json')['name'], 'test.hello')

    def test_dependency_cycle_missing_and_order(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for ident in ('test.a', 'test.b'):
                self.mod(root, ident, True)
            mods = kit.discover(root)
            mods['test.a']['requires']['test.b'] = '0.1.0'
            self.assertEqual(kit.load_order(mods), ['test.b', 'test.a'])
            mods['test.b']['requires']['test.a'] = '0.1.0'
            with self.assertRaises(kit.ModError): kit.load_order(mods)
            mods['test.b']['requires'] = {'test.missing': '0.1.0'}
            with self.assertRaises(kit.ModError): kit.load_order(mods)

    def test_required_dependency_cannot_hide_as_local(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.mod(root, 'test.a', True); self.mod(root, 'test.b')
            mods = kit.discover(root); mods['test.a']['requires']['test.b'] = '0.1.0'
            with self.assertRaises(kit.ModError): kit.load_order(mods)

    def test_content_changes_detected_but_json_format_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            folder = self.mod(Path(d), 'test.hello')
            before = kit.package_hash(folder)
            path = folder / 'mod.json'
            path.write_text(json.dumps(kit.read_json(path), sort_keys=True), encoding='utf-8')
            self.assertEqual(kit.package_hash(folder), before)
            (folder / 'Scripts/main.lua').write_text('print("changed")', encoding='utf-8')
            self.assertNotEqual(kit.package_hash(folder), before)

    def test_path_traversal_and_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            folder = self.mod(Path(d), 'test.hello')
            manifest = kit.read_json(folder / 'mod.json')
            for value in ('../outside.lua', 'C:/outside.lua', '/outside.lua', '..\\outside.lua'):
                manifest['entrypoint'] = value
                with self.assertRaises(kit.ModError): kit.validate_manifest(manifest, folder)
            file = folder / 'duplicate.json'; file.write_text('{"id":1,"id":2}')
            with self.assertRaises(kit.ModError): kit.read_json(file)

    def test_peers_local_mods_and_personal_photos_do_not_need_to_match(self):
        host = self.profile(); peer = copy.deepcopy(host)
        host['local_mods'] = [{'id': 'test.local_a'}]
        peer['local_mods'] = [{'id': 'test.local_b'}]
        # Photo payloads are outside mod packages and never appear in this profile.
        self.assertTrue(kit.compare_profiles(host, peer)['compatible_offline'])
        self.assertFalse(kit.compare_profiles(host, peer)['runtime_handshake_implemented'])

    def test_peer_missing_changed_or_extra_shared_mod_is_rejected(self):
        host = self.profile()
        host['shared_mods'].append({'id': 'test.rules', 'version': '1.0.0', 'package_sha256': 'c' * 64})
        peer = self.profile()
        self.assertEqual(kit.compare_profiles(host, peer)['issues'][0]['code'], 'missing_required_mod')
        peer = copy.deepcopy(host); peer['shared_mods'][1]['package_sha256'] = 'd' * 64
        self.assertEqual(kit.compare_profiles(host, peer)['issues'][0]['code'], 'different_mod_files')
        peer = copy.deepcopy(host); peer['game_sha256'] = 'e' * 64
        self.assertEqual(kit.compare_profiles(host, peer)['issues'][0]['code'], 'different_game_sha256')

    def test_duplicate_peer_ids_rejected(self):
        peer = self.profile(); peer['shared_mods'] *= 2
        with self.assertRaises(kit.ModError): kit.compare_profiles(self.profile(), peer)


if __name__ == '__main__': unittest.main()
