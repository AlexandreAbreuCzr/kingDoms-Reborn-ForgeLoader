"""Fetch and verify the pinned Lua and JSON sources in the local build cache."""
from pathlib import Path
import hashlib
import json
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def setup():
    config = json.loads((ROOT / 'profiles/loader-dependencies.json').read_text())
    output = ROOT / '.local/loader-deps'
    output.mkdir(parents=True, exist_ok=True)
    for name, row in config.items():
        target = output / ('lua.tar.gz' if name == 'lua' else 'json.hpp')
        if not target.exists():
            target.write_bytes(urllib.request.urlopen(row['url'], timeout=60).read())
        if hashlib.sha256(target.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError(f'{name} dependency hash mismatch; cached file preserved')
    lua = output / ('lua-' + config['lua']['version'])
    with tarfile.open(output / 'lua.tar.gz') as archive:
        # Validate the exact upstream archive and keep all paths under its version directory.
        for entry in archive.getmembers():
            target = (output / entry.name).resolve()
            if not target.is_relative_to(lua.resolve()) or not (entry.isfile() or entry.isdir()):
                raise ValueError('Unexpected Lua archive member')
        if not lua.exists(): archive.extractall(output)
        for entry in archive.getmembers():
            if entry.isfile() and (output / entry.name).read_bytes() != archive.extractfile(entry).read():
                raise ValueError('Extracted Lua source differs from pinned archive: ' + entry.name)
    print('Verified Lua ' + config['lua']['version'] + ' and nlohmann/json ' + config['json']['version'])


if __name__ == '__main__': setup()
