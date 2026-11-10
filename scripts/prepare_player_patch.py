"""Create a small PE-header patch; never distribute the original game image."""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = '8f2653ba07d53c3e01eb68a3f0a9a5851ef96e84d42181a5dd7a279740d0033c'
TARGET_SHA = 'a5d2385660d9e819d2aa073cdd9c1d74c05149c9617f37cbb8b31e83708c4e24'
DLL_SHA = '51ca84fbfd4918547a7a974a14095906548e5e7d1e170dcace2dfe26802de547'


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
            'general_mod_loader': True, 'runtime': 'forgeloader-0.2.0',
            'upgrade_from_dll_sha256': ['3664b38d0c53d03bdc5b90d7f04748a64f7234fb0c9ae9cc547940c865b8a3a1'], 'noasync_patch_applied': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    patch = create_patch(args.source.read_bytes(), args.target.read_bytes())
    output = ROOT / 'profiles/player-patch.json'
    output.write_text(json.dumps(patch, indent=2) + '\n', encoding='utf-8')
    print(f'{output}: {output.stat().st_size} bytes')
