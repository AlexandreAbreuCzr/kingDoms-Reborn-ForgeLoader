"""Verify PE imports and executable code survive the new runtime dependency."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest
import tempfile
from unittest.mock import patch
import contextlib
import io
import os

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.local/kr214-input/PrototypeCity-Win64-Shipping.exe'
if os.environ.get('KINGDOMS_ORIGINAL_EXE'): SOURCE = Path(os.environ['KINGDOMS_ORIGINAL_EXE'])
spec = importlib.util.spec_from_file_location('portrait_builder', ROOT / 'scripts/build_portrait_exe.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def parse(raw):
    pe = struct.unpack_from('<I', raw, 0x3c)[0]
    opt = pe + 24
    start = opt + struct.unpack_from('<H', raw, pe + 20)[0]
    sections = []
    for i in range(struct.unpack_from('<H', raw, pe + 6)[0]):
        pos = start + i * 40
        sections.append(struct.unpack_from('<8sIIIIIIHHI', raw, pos))
    def offset(rva):
        for s in sections:
            if s[2] <= rva < s[2] + s[3]:
                return s[4] + rva - s[2]
        raise AssertionError('RVA outside file-backed sections')
    at = offset(struct.unpack_from('<I', raw, opt + 120)[0])
    imports = []
    while raw[at:at + 20] != bytes(20):
        desc = raw[at:at + 20]
        ilt, _, _, name, iat = struct.unpack('<IIIII', desc)
        p = offset(name)
        dll = raw[p:raw.index(b'\0', p)].decode('ascii')
        imports.append((desc, dll, ilt, iat))
        at += 20
    return sections, imports, offset


@unittest.skipUnless(SOURCE.exists() and hashlib.sha256(SOURCE.read_bytes()).hexdigest() == '29dd825cb3da3e79485fed017bf5c219af81b72dc01c0a351a2764b12e8134c2', 'Exact original game fixture required')
class PortraitExecutableTests(unittest.TestCase):
    def test_shipped_portrait_build_keeps_original_graphics_policy(self):
        # Exercise build(), not just its PE helper: the v1 regression happened here.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'profiles').mkdir()
            (root / 'profiles/player-patch.json').write_bytes((ROOT / 'profiles/player-patch.json').read_bytes())
            with patch.object(builder, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                target = builder.build(SOURCE)
            data = target.read_bytes()
            raw = SOURCE.read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),
                             'c676d4ac5533464cc2bbfefd6321c9a119d0f264069ddf265668f22d945d3df4')
            for section in parse(raw)[0]:
                at, length = section[4], section[3]
                self.assertEqual(data[at:at + length], raw[at:at + length])

    def test_existing_code_and_imports_preserved(self):
        raw = SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '29dd825cb3da3e79485fed017bf5c219af81b72dc01c0a351a2764b12e8134c2')
        modified, meta = builder.add_runtime(raw)
        old, imports, _ = parse(raw)
        new, after, offset = parse(modified)
        self.assertEqual(old, new[:-1])
        self.assertEqual(imports, after[:-1])
        for section in old:
            at, length = section[4], section[3]
            self.assertEqual(raw[at:at + length], modified[at:at + length])
        desc, name, ilt, iat = after[-1]
        self.assertEqual(name, 'KingdomsPortraits.dll')
        self.assertEqual(modified[offset(ilt):offset(ilt) + 16], modified[offset(iat):offset(iat) + 16])
        entry = struct.unpack_from('<Q', modified, offset(ilt))[0]
        at = offset(entry) + 2
        self.assertEqual(modified[at:modified.index(b'\0', at)], b'KingdomsPortraitsMarker')
        self.assertEqual(new[-1][-1] & 0x20000000, 0, 'Added data section must not be executable')
        self.assertEqual(meta['preserved_original_import_descriptors'], len(imports))
        self.assertEqual(SOURCE.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
