"""Kingdoms ModKit: project templates and OFFLINE compatibility profiles.

This tool does not load mods into the game or enforce a network handshake.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

VERSION = '0.1.0-alpha'
API_MAJOR = 1
GAME_SHA = 'a5d2385660d9e819d2aa073cdd9c1d74c05149c9617f37cbb8b31e83708c4e24'
PORTRAITS_SHA = '3664b38d0c53d03bdc5b90d7f04748a64f7234fb0c9ae9cc547940c865b8a3a1'
ID = re.compile(r'^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$')
SEMVER = re.compile(r'^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$')
HASH = re.compile(r'^[0-9a-f]{64}$')


class ModError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ModError(f'Chave JSON duplicada: {key}')
            result[key] = value
        return result
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                          parse_constant=lambda token: (_ for _ in ()).throw(ModError(f'JSON invalido: {token}')))
    except (OSError, ValueError) as error:
        raise ModError(f'{path}: {error}') from error


def relative_file(folder, value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ModError('entrypoint deve ser um caminho relativo com /')
    part = PurePosixPath(value)
    if part.is_absolute() or '..' in part.parts or not part.parts:
        raise ModError('entrypoint fora da pasta do mod')
    result = (folder / value).resolve()
    if not result.is_relative_to(folder.resolve()) or not result.is_file():
        raise ModError(f'Arquivo de entrada ausente ou externo: {value}')
    return result


def validate_manifest(manifest, folder):
    if not isinstance(manifest, dict) or type(manifest.get('schema')) is not int or manifest['schema'] != 1:
        raise ModError('Manifesto precisa de schema 1')
    ident = manifest.get('id', '')
    if not isinstance(ident, str) or not ID.fullmatch(ident) or ident.startswith('core.'):
        raise ModError('ID deve usar autor.nome; prefixo core. reservado')
    if not isinstance(manifest.get('name'), str) or not manifest['name'].strip():
        raise ModError(f'{ident}: nome ausente')
    if not isinstance(manifest.get('version'), str) or not SEMVER.fullmatch(manifest['version']):
        raise ModError(f'{ident}: version deve ser X.Y.Z')
    if type(manifest.get('api_major')) is not int or manifest['api_major'] != API_MAJOR:
        raise ModError(f'{ident}: API major incompativel')
    if type(manifest.get('enabled', True)) is not bool:
        raise ModError(f'{ident}: enabled deve ser booleano')
    if manifest.get('multiplayer') not in ('local', 'required'):
        raise ModError(f'{ident}: multiplayer deve ser local ou required')
    if manifest.get('runtime') not in ('ue4ss-lua', 'ue4ss-native'):
        raise ModError(f'{ident}: runtime nao reconhecido')
    builds = manifest.get('game_builds')
    if not isinstance(builds, list) or not builds or not all(isinstance(x, str) and HASH.fullmatch(x) for x in builds):
        raise ModError(f'{ident}: game_builds precisa de hashes SHA-256 explicitos')
    dependencies = manifest.get('requires', {})
    if not isinstance(dependencies, dict) or not all(isinstance(k, str) and ID.fullmatch(k) and isinstance(v, str) and SEMVER.fullmatch(v) for k, v in dependencies.items()):
        raise ModError(f'{ident}: dependencias precisam de ID e versao exata')
    conflicts = manifest.get('conflicts', [])
    if not isinstance(conflicts, list) or not all(isinstance(x, str) and ID.fullmatch(x) for x in conflicts):
        raise ModError(f'{ident}: lista de conflitos invalida')
    relative_file(folder, manifest.get('entrypoint'))
    return manifest


def package_hash(folder):
    files, seen = [], set()
    for item in sorted(folder.rglob('*')):
        if item.is_symlink():
            raise ModError(f'Link simbolico fora do formato de pacote: {item.name}')
        if item.is_file():
            if not item.resolve().is_relative_to(folder.resolve()):
                raise ModError('Arquivo fora da pasta do mod')
            name = item.relative_to(folder).as_posix()
            if name.casefold() in seen:
                raise ModError(f'Caminhos com colisao de maiusculas: {name}')
            seen.add(name.casefold())
            # JSON whitespace/key order should not create a false incompatibility.
            sha = hashlib.sha256(canonical(read_json(item))).hexdigest() if item.suffix.lower() == '.json' else digest(item)
            files.append({'path': name, 'sha256': sha})
    return hashlib.sha256(canonical(files)).hexdigest()


def discover(folder):
    if not folder.is_dir():
        raise ModError('Pasta de mods inexistente')
    mods = {}
    for path in sorted(folder.glob('*/mod.json')):
        manifest = validate_manifest(read_json(path), path.parent)
        if not manifest.get('enabled', True):
            continue
        ident = manifest['id']
        if ident in mods:
            raise ModError(f'ID duplicado: {ident}')
        mods[ident] = {**manifest, 'package_sha256': package_hash(path.parent)}
    return mods


def load_order(mods):
    versions = {'core.shared_portraits': '3.0.0', **{key: m['version'] for key, m in mods.items()}}
    for ident, mod in mods.items():
        for dep, version in mod.get('requires', {}).items():
            if versions.get(dep) != version:
                raise ModError(f'{ident} exige {dep} {version}; encontrado {versions.get(dep, "ausente")}')
            if mod['multiplayer'] == 'required' and dep in mods and mods[dep]['multiplayer'] != 'required':
                raise ModError(f'{ident}: dependencia compartilhada marcada como local: {dep}')
        for conflict in mod.get('conflicts', []):
            if conflict in versions:
                raise ModError(f'Conflito entre {ident} e {conflict}')
    ordered, visiting, visited = [], set(), set()
    def visit(ident):
        if ident in visiting:
            raise ModError(f'Ciclo de dependencias em {ident}')
        if ident in visited:
            return
        visiting.add(ident)
        for dep in sorted(mods[ident].get('requires', {})):
            if dep in mods:
                visit(dep)
        visiting.remove(ident)
        visited.add(ident)
        ordered.append(ident)
    for ident in sorted(mods):
        visit(ident)
    return ordered


def make_profile(exe, mods_folder):
    if digest(exe) != GAME_SHA:
        raise ModError('Build sem adaptador confirmado: este prototipo aceita somente o EXE de retratos v3')
    photo_dll = exe.parent / 'KingdomsPortraits.dll'
    if not photo_dll.is_file() or digest(photo_dll) != PORTRAITS_SHA:
        raise ModError('Modulo padrao de retratos v3 ausente ou diferente')
    mods = discover(mods_folder)
    ordered = load_order(mods)
    for ident, mod in mods.items():
        if GAME_SHA not in mod['game_builds']:
            raise ModError(f'{ident} nao declara suporte a este build')
    shared = [{'id': 'core.shared_portraits', 'version': '3.0.0', 'package_sha256': PORTRAITS_SHA}]
    local = []
    for ident in ordered:
        mod = mods[ident]
        row = {key: mod[key] for key in ('id', 'version', 'package_sha256')}
        (shared if mod['multiplayer'] == 'required' else local).append(row)
    return {'schema': 1, 'tool_version': VERSION, 'api_major': API_MAJOR,
            'adapter': 'kr-0.253-win64-portraits-v3', 'game_sha256': GAME_SHA,
            'shared_mods': sorted(shared, key=lambda x: x['id']), 'local_mods': local,
            'load_order': ordered, 'mode': 'offline-profile', 'runtime_handshake_implemented': False}


def validate_profile(profile):
    if not isinstance(profile, dict) or profile.get('schema') != 1 or type(profile.get('api_major')) is not int:
        raise ModError('Perfil de compatibilidade invalido')
    if not isinstance(profile.get('game_sha256'), str) or not HASH.fullmatch(profile['game_sha256']):
        raise ModError('Hash do jogo invalido no perfil')
    if not isinstance(profile.get('adapter'), str):
        raise ModError('Adaptador ausente no perfil')
    rows = profile.get('shared_mods')
    if not isinstance(rows, list) or len(rows) > 256:
        raise ModError('Lista de mods compartilhados invalida')
    found = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ModError('Entrada de mod invalida no perfil')
        ident, version, sha = (row.get(k) for k in ('id', 'version', 'package_sha256'))
        if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in found:
            raise ModError('ID invalido ou duplicado no perfil')
        if not isinstance(version, str) or not SEMVER.fullmatch(version) or not isinstance(sha, str) or not HASH.fullmatch(sha):
            raise ModError(f'Versao/hash invalido no perfil: {ident}')
        found[ident] = row
    if 'core.shared_portraits' not in found:
        raise ModError('Perfil sem modulo padrao de retratos')
    return found


def compare_profiles(host, peer):
    expected, actual = validate_profile(host), validate_profile(peer)
    issues = []
    for field in ('api_major', 'adapter', 'game_sha256'):
        if host[field] != peer[field]:
            issues.append({'code': 'different_' + field, 'expected': host[field], 'actual': peer[field]})
    for ident in sorted(expected.keys() | actual.keys()):
        if ident not in actual:
            issues.append({'code': 'missing_required_mod', 'id': ident})
        elif ident not in expected:
            issues.append({'code': 'extra_required_mod', 'id': ident})
        elif expected[ident]['version'] != actual[ident]['version']:
            issues.append({'code': 'different_mod_version', 'id': ident})
        elif expected[ident]['package_sha256'] != actual[ident]['package_sha256']:
            issues.append({'code': 'different_mod_files', 'id': ident})
    return {'compatible_offline': not issues, 'issues': issues,
            'runtime_handshake_implemented': False,
            'meaning': 'Comparacao de perfis; nao comprova compatibilidade real da partida nem autenticidade do cliente.'}


def new_mod(folder, ident, name, required=False):
    if not ID.fullmatch(ident) or ident.startswith('core.'):
        raise ModError('Use um ID como autor.meu_mod')
    if not isinstance(name, str) or not name.strip():
        raise ModError('Nome do mod ausente')
    if folder.exists():
        raise ModError('Destino ja existe; arquivos preservados')
    manifest = {'schema': 1, 'id': ident, 'name': name, 'version': '0.1.0', 'api_major': API_MAJOR,
                'runtime': 'ue4ss-lua', 'entrypoint': 'Scripts/main.lua', 'game_builds': [GAME_SHA],
                'multiplayer': 'required' if required else 'local', 'enabled': True,
                'requires': {'core.shared_portraits': '3.0.0'}, 'conflicts': [], 'settings': {}}
    (folder / 'Scripts').mkdir(parents=True)
    (folder / 'mod.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (folder / 'Scripts/main.lua').write_text(f'-- Requires a compatible UE4SS runtime; ModKit does not load this yet.\nprint("[{ident}] Lua mod initialized\\n")\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    new = sub.add_parser('new'); new.add_argument('id'); new.add_argument('--name', required=True); new.add_argument('--output', type=Path, required=True); new.add_argument('--required', action='store_true')
    check = sub.add_parser('validate'); check.add_argument('mods', type=Path)
    lock = sub.add_parser('profile'); lock.add_argument('--game-exe', type=Path, required=True); lock.add_argument('--mods', type=Path, required=True); lock.add_argument('--output', type=Path, required=True)
    compare = sub.add_parser('compare'); compare.add_argument('host', type=Path); compare.add_argument('peer', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'new':
            result = new_mod(args.output, args.id, args.name, args.required)
        elif args.command == 'validate':
            mods = discover(args.mods)
            result = {'valid': True, 'load_order': load_order(mods), 'runtime_loaded': False}
        elif args.command == 'profile':
            result = make_profile(args.game_exe, args.mods)
            if args.output.exists():
                raise ModError('Perfil de destino ja existe; escolha outro arquivo')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        else:
            result = compare_profiles(read_json(args.host), read_json(args.peer))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if args.command == 'compare' and result['issues'] else 0
    except (ModError, OSError) as error:
        parser.exit(1, f'Erro: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
