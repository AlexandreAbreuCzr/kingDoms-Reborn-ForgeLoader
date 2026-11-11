"""Create a small PE-header patch; never distribute the original game image."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = '29dd825cb3da3e79485fed017bf5c219af81b72dc01c0a351a2764b12e8134c2'
TARGET_SHA = 'c676d4ac5533464cc2bbfefd6321c9a119d0f264069ddf265668f22d945d3df4'
DLL_SHA = '2fe5903e5da5021c0643df744552480f1e1f392828737e94ceaf3b8879988e98'


def create_patch(source, target):
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA or hashlib.sha256(target).hexdigest() != TARGET_SHA:
        raise ValueError('Exact original and portraits-v3 images required')
    pe = struct.unpack_from('<I', source, 0x3c)[0]
    headers = struct.unpack_from('<I', source, pe + 24 + 60)[0]
    if source[headers:] != target[headers:len(source)]:
        raise ValueError('Changes outside PE headers; original code must be preserved')
    changes = []
    at = 0
    while at < headers:
        if source[at] == target[at]:
            at += 1
            continue
        start = at
        while at < headers and source[at] != target[at]: at += 1
        changes.append({'offset': start, 'before': source[start:at].hex(), 'after': target[start:at].hex()})
    return {'schema': 1, 'source_sha256': SOURCE_SHA, 'target_sha256': TARGET_SHA,
            'dll_sha256': DLL_SHA, 'source_length': len(source), 'target_length': len(target),
            'changes': changes, 'append_hex': target[len(source):].hex(),
            'general_mod_loader': True, 'runtime': 'forgeloader-0.2.1-kr214',
            'upgrade_from_dll_sha256': ['918065303e736524d3cff6d6b2b945834eefd2d904cd23c643b7f8140b4bf23a', '7bf6e1f556176c82cc06c9fe3cfd5e0b719c110a7ebbe6907e7261b1cd8d9165', '33d25a4dc94c83b8f74682da75997781c88af06ffba5eb615819e0cb82cea776', '94161f15cd84e874aa6ce5fb782290a6164a5d7b27bfdd0d91d0e3d89eabc6c8', 'b166877b07a5e91e71f0d7de0652e0aeb3706ed6988d0f4bea30e251f7ca9a0c'], 'noasync_patch_applied': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    patch = create_patch(args.source.read_bytes(), args.target.read_bytes())
    output = ROOT / 'profiles/player-patch.json'
    output.write_text(json.dumps(patch, indent=2) + '\n', encoding='utf-8')
    print(f'{output}: {output.stat().st_size} bytes')
