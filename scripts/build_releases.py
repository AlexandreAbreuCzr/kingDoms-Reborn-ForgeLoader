"""Build separate ForgeLoader player and developer downloads from allowlists."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(path, files):
    if len(files) != len(set(files)):
        raise ValueError('Duplicate archive members')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, source in sorted(files.items()):
            raw = source.read_bytes()
            if name.endswith(('.cmd', '.ps1')):
                raw = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            z.writestr(info, raw, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(path) as z:
        if z.testzip() or set(z.namelist()) != set(files):
            raise ValueError('Archive verification failed')
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path)}


def devkit_files():
    files = {}
    for folder in ('modkit', 'mods', 'native/portraits', 'native/loader', '.agents/skills', 'third_party'):
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and (path.suffix in ('.py', '.json', '.md', '.cpp', '.h', '.hpp', '.lua', '.txt', '.yaml') or path.name == 'CMakeLists.txt'):
                files[path.relative_to(ROOT).as_posix()] = path
    for name in ('README.md', 'AGENTS.md', 'CRIAR-MOD-COM-IA.md', 'Abrir-DevKit.cmd', 'release.json', 'profiles/noasync-binary-patch.json', 'profiles/player-patch.json',
                 'scripts/build_portrait_exe.py', 'scripts/build_portraits.ps1', 'scripts/setup_native.ps1',
                 'scripts/build_releases.py', 'scripts/build_modkit.py', 'scripts/prepare_player_patch.py',
                 'scripts/setup_loader.py', 'profiles/loader-dependencies.json', 'docs/MOD-API.md', 'docs/VALIDATION-0.2.0.md',
                 'tests/test_modkit.py', 'tests/test_portrait_exe.py', 'tests/test_save_repair.py',
                 'docs/KR214.md', 'tools/repair_save_players.py', 'installer/Reparar-Save.cmd',
                 'docs/DEVELOPMENT.md', 'docs/PLAYERS.md', 'docs/STATUS.md', 'docs/ROADMAP.md', 'third_party/MinHook-LICENSE.txt',
                 'installer/Setup-ForgeLoader.ps1', 'installer/Instalar-ForgeLoader.cmd', 'installer/Restaurar-Backup.cmd', 'installer/Install-Mod.ps1', 'installer/Instalar-Mod.cmd'):
        files[name] = ROOT / name
    files['LEIA-ME-DEVKIT.md'] = ROOT / 'docs/DEVELOPMENT.md'
    files['STATUS.md'] = ROOT / 'docs/STATUS.md'
    return files


def build(dll=None, devkit_only=False):
    config = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))
    output = ROOT / 'dist/releases' / config['tag']
    output.mkdir(parents=True, exist_ok=True)
    result = [archive(output / config['devkit_archive'], devkit_files())]
    if not devkit_only:
        if dll is None: raise ValueError('--runtime-dll is required for the player package')
        dll = Path(dll)
        patch = json.loads((ROOT / 'profiles/player-patch.json').read_text())
        if sha(dll) != patch['dll_sha256']: raise ValueError('Runtime DLL differs from validated build')
        files = {
            'Instalar-ForgeLoader.cmd': ROOT / 'installer/Instalar-ForgeLoader.cmd',
            'Restaurar-Backup.cmd': ROOT / 'installer/Restaurar-Backup.cmd',
            'Setup-ForgeLoader.ps1': ROOT / 'installer/Setup-ForgeLoader.ps1',
            'Install-Mod.ps1': ROOT / 'installer/Install-Mod.ps1',
            'Instalar-Mod.cmd': ROOT / 'installer/Instalar-Mod.cmd',
            'Reparar-Save.cmd': ROOT / 'installer/Reparar-Save.cmd',
            'Ferramentas/repair_save_players.py': ROOT / 'tools/repair_save_players.py',
            'payload/player-patch.json': ROOT / 'profiles/player-patch.json',
            'payload/KingdomsPortraits.dll': dll,
            'LEIA-ME-PRIMEIRO.md': ROOT / 'docs/PLAYERS.md',
            'KR214.md': ROOT / 'docs/KR214.md',
            'STATUS.md': ROOT / 'docs/STATUS.md',
            'LICENSE-MINHOOK.txt': ROOT / 'third_party/MinHook-LICENSE.txt',
            'LICENSE-LUA.txt': ROOT / 'third_party/Lua-LICENSE.txt',
            'LICENSE-JSON.txt': ROOT / 'third_party/nlohmann-json-LICENSE.txt',
        }
        result.insert(0, archive(output / config['player_archive'], files))
        for folder in sorted((ROOT / 'modkit/examples/forgeloader').iterdir()):
            if folder.is_dir():
                assets = {p.relative_to(folder).as_posix(): p for p in folder.rglob('*') if p.is_file()}
                result.append(archive(output / (folder.name + '-1.0.0.flmod'), assets))
        native=dll.parent/'forge_native.dll'
        if not native.is_file(): raise ValueError('Build the native example before packaging')
        result.append(archive(output/'forge.native_hello-1.0.0.flmod', {'mod.json': ROOT/'modkit/examples/native/forge_native/mod.json', 'dlls/main.dll': native}))
        performance=dll.parent/'forge_kr214_performance.dll'
        if not performance.is_file(): raise ValueError('Build the KR214 performance mod before packaging')
        name='forge.kr214_performance-1.0.0.flmod'
        result.append(archive(output/name, {'mod.json': ROOT/'mods/forge.kr214_performance/mod.json', 'dlls/main.dll': performance, 'LEIA-ME.md': ROOT/'docs/KR214.md'}))
        files['mods-exemplo/'+name]=output/name
        files['mods-exemplo/forge.hello-1.0.0.flmod']=output/'forge.hello-1.0.0.flmod'
        files['mods-exemplo/forge.fps_limit-1.0.0.flmod']=output/'forge.fps_limit-1.0.0.flmod'
        result[0]=archive(output / config['player_archive'], files)
    sums = ''.join(f"{row['sha256']}  {row['file']}\n" for row in result)
    (output / 'SHA256SUMS.txt').write_text(sums, encoding='ascii')
    manifest = {'name': config['name'], 'version': config['version'], 'artifacts': result,
                'contains_original_game': False, 'general_mod_loader': config['general_mod_loader'],
                'game_build': config['game_build'], 'status': 'KR214 port; multiplayer save/rejoin and performance gains on GTX 1080 not verified'}
    (output / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'output': str(output), **manifest}, indent=2))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dll', type=Path)
    parser.add_argument('--devkit-only', action='store_true')
    args = parser.parse_args()
    build(args.runtime_dll, args.devkit_only)
