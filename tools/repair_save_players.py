"""Recover vacant multiplayer slots in a new KR214 save directory.

The player records are taken from an explicitly chosen older save of the same
world. This tool does not convert saves between game versions.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tempfile

EMPTY_STEAM = (1 << 64) - 1
MAX_METADATA = 2 * 1024 * 1024


class SaveError(ValueError):
    pass


class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, size):
        if not 0 <= size <= len(self.data) - self.pos:
            raise SaveError('MetaData.dat incompleto ou incompatível')
        at = self.pos
        self.pos += size
        return self.data[at:self.pos]

    def read(self, fmt):
        return struct.unpack('<' + fmt, self.take(struct.calcsize('<' + fmt)))[0]

    def boolean(self):
        value = self.read('I')
        if value not in (0, 1):
            raise SaveError('Flag de metadados inválida')
        return bool(value)

    def string(self):
        n = self.read('i')
        if not n:
            return ''
        if abs(n) > 16384:
            raise SaveError('Comprimento de texto inválido no save')
        width = 1 if n > 0 else 2
        raw = self.take(abs(n) * width)
        if raw[-width:] != b'\0' * width:
            raise SaveError('Texto sem terminador no save')
        try:
            return raw[:-width].decode('cp1252' if n > 0 else 'utf-16le')
        except UnicodeError as exc:
            raise SaveError('Texto inválido no save') from exc


@dataclass(frozen=True)
class Record:
    raw: bytes
    name: str
    steam_id: int
    slot: int

    @property
    def empty(self):
        return not self.name and self.steam_id == EMPTY_STEAM and self.slot == -1

    @property
    def occupied(self):
        return bool(self.name) and self.steam_id not in (0, EMPTY_STEAM) and 0 <= self.slot < 64


@dataclass
class Meta:
    header: bytes
    version: int
    players: list[Record]
    tail: bytes
    date: int
    ticks: int
    map_signature: bytes
    single_player: bool

    def serialize(self):
        return self.header + b''.join(p.raw for p in self.players) + self.tail


def parse_meta(data: bytes) -> Meta:
    r = Reader(data)
    version = r.read('I')
    if version // 1_000_000 not in (206,214):
        raise SaveError(f'Layout de save não suportado: {version}. Use saves da versão antiga 0.206 ou 0.214.')
    count = r.read('i')
    if not 1 <= count <= 64:
        raise SaveError('Contagem de slots incompatível')
    players = []
    for index in range(count):
        start = r.pos
        r.read('I')  # FText flags
        if r.read('b') != -1:
            raise SaveError('Formato de nome FText incompatível')
        name = r.string() if r.boolean() else ''
        steam_id, slot = r.read('Q'), r.read('i')
        r.take(36)  # logoIndex + two FLinearColor values
        r.string()  # portraitName, preserved verbatim
        r.take(8)   # factionIndex + coopTargetPlayerId
        player = Record(data[start:r.pos], name, steam_id, slot)
        if player.occupied and slot != index:
            raise SaveError('Identidade do jogador não corresponde ao slot do save')
        players.append(player)
    tail = data[r.pos:]
    r.string()  # Display title, not a world identifier.
    date, ticks = r.read('q'), r.read('i')
    r.read('i')  # population
    start = r.pos
    terrain = r.read('q')
    seed = r.string()
    if not seed or not 1 <= terrain <= 1000 or date <= 0 or ticks < 0:
        raise SaveError('Mapa ou data do save não puderam ser validados')
    r.take(8)  # int32 map size + four uint8 terrain parameters
    r.boolean()  # equator setting
    r.take(9)  # player count, AI count, difficulty
    if terrain >= 5:
        r.boolean()  # deck mode
        r.boolean()  # peaceful AI
    single = r.boolean()
    signature = data[start:r.pos]
    for _ in range(2):  # GameSaveInfo checksum and compressedDataSize arrays
        n = r.read('i')
        if not 0 <= n <= 65536:
            raise SaveError('Tabela de dados do save inválida')
        r.take(n * 4)
    n = r.read('i')  # GameSaveInfo::success, serialized as an array of bytes.
    if not 0 <= n <= 65536:
        raise SaveError('Tabela de status do save inválida')
    r.take(n)
    if r.pos != len(data):
        raise SaveError('Campos extras em MetaData.dat; layout não confirmado')
    ids = [p.steam_id for p in players if p.occupied]
    if len(ids) != len(set(ids)):
        raise SaveError('IDs de jogadores duplicados nos metadados')
    return Meta(data[:8], version, players, tail, date, ticks, signature, single)


def load(folder):
    p = folder / 'MetaData.dat'
    if p.stat().st_size > MAX_METADATA:
        raise SaveError('MetaData.dat excede o limite')
    return parse_meta(p.read_bytes())


def plan(damaged, donor):
    damaged, donor = damaged.resolve(), donor.resolve()
    if damaged == donor:
        raise SaveError('Escolha dois saves diferentes')
    target, previous = load(damaged), load(donor)
    if target.version != previous.version or len(target.players) != len(previous.players):
        raise SaveError('O doador precisa ter a mesma versão e contagem de slots')
    if target.single_player or previous.single_player:
        raise SaveError('Esta ferramenta é para saves multiplayer')
    if target.map_signature != previous.map_signature:
        raise SaveError('As configurações e a semente do mapa não coincidem')
    if not (previous.date < target.date and previous.ticks <= target.ticks):
        raise SaveError('O doador precisa ser anterior pela data e progresso gravados no save')
    if not any(a.occupied and b.occupied and a.steam_id == b.steam_id for a,b in zip(target.players,previous.players)):
        raise SaveError('Não há jogador em comum no mesmo slot para validar o doador')
    present = {p.steam_id for p in target.players if p.occupied}
    replacements = {}
    for index,(current,candidate) in enumerate(zip(target.players,previous.players)):
        if current.empty and candidate.occupied and candidate.steam_id not in present:
            replacements[index] = candidate
            present.add(candidate.steam_id)
    return target,replacements


def fingerprint(folder):
    files = {}
    for path in sorted(folder.rglob('*')):
        stat = path.lstat()
        if path.is_symlink() or getattr(stat,'st_file_attributes',0) & 0x400 or not path.resolve().is_relative_to(folder):
            raise SaveError('Save contém link ou redirecionamento')
        if path.is_dir(): continue
        if not path.is_file(): raise SaveError('Entrada inesperada no save')
        h = hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda: f.read(1024*1024),b''): h.update(block)
        files[path.relative_to(folder).as_posix()] = h.hexdigest()
    if not any(re.fullmatch(r'GameData[^/]*\.dat', name, re.I) for name in files):
        raise SaveError('Não foram encontrados arquivos GameData no save')
    return files


def repair(damaged, donor, output):
    damaged, donor, output = damaged.resolve(), donor.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(damaged) or output.is_relative_to(donor):
        raise SaveError('Escolha uma pasta nova fora dos saves de origem')
    target,replacements = plan(damaged,donor)
    if not replacements: raise SaveError('Nenhum slot vazio recuperável neste par de saves')
    before = fingerprint(damaged)
    if before.get('MetaData.dat') != hashlib.sha256(target.serialize()).hexdigest():
        raise SaveError('O save mudou durante a leitura. Feche o jogo e tente de novo.')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.kr214-reparo-',dir=output.parent) as temp:
        temp_root = Path(temp).resolve()
        if temp_root.parent != output.parent: raise SaveError('Pasta temporária inesperada')
        stage = temp_root / 'save'
        shutil.copytree(damaged,stage)
        if fingerprint(stage) != before or fingerprint(damaged) != before:
            raise SaveError('A cópia não corresponde ao original; o jogo pode estar salvando')
        for index,record in replacements.items(): target.players[index] = record
        (stage / 'MetaData.dat').write_bytes(target.serialize())
        if load(stage).serialize() != target.serialize(): raise SaveError('A cópia reparada não pôde ser verificada')
        after = fingerprint(stage)
        if any(after.get(name) != sha for name,sha in before.items() if name != 'MetaData.dat'):
            raise SaveError('Arquivo de simulação foi alterado; cópia recusada')
        if output.exists(): raise SaveError('A pasta de destino já existe')
        stage.rename(output)
    return sorted(replacements)


def gui():
    import tkinter as tk
    from tkinter import filedialog,messagebox
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    start=Path(os.environ.get('LOCALAPPDATA','.'))/'PunCity/Saved/GameSaves'
    try:
        damaged=filedialog.askdirectory(parent=root,title='Selecione a pasta do save que perdeu jogadores',initialdir=start)
        if not damaged:return 0
        donor=filedialog.askdirectory(parent=root,title='Selecione um save anterior do MESMO mundo',initialdir=Path(damaged).parent)
        if not donor:return 0
        damaged,donor=Path(damaged),Path(donor)
        _,replacements=plan(damaged,donor)
        if not replacements:raise SaveError('Nenhum slot vazio recuperável neste par de saves')
        output=damaged.parent/('Reparado-'+damaged.name)
        if messagebox.askyesno('Reparar save KR214',f'Recuperar {len(replacements)} slot(s) numa cópia?\n\n{output.name}',parent=root):
            repair(damaged,donor,output)
            messagebox.showinfo('Reparar save KR214',f'Cópia criada:\n{output}\nO original foi preservado.',parent=root)
        return 0
    except (OSError,SaveError) as exc:
        messagebox.showerror('Reparar save KR214',str(exc),parent=root);return 1
    finally:root.destroy()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    modes=parser.add_subparsers(dest='mode',required=True)
    modes.add_parser('gui')
    for name in ('plan','repair'):
        cmd=modes.add_parser(name);cmd.add_argument('save',type=Path);cmd.add_argument('--donor',type=Path,required=True)
        if name=='repair':cmd.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.mode=='gui':return gui()
        if args.mode=='plan':
            _,slots=plan(args.save,args.donor);print('Slots recuperáveis:',', '.join(map(str,slots)) or 'nenhum');return 0
        output=args.output or args.save.parent/('Reparado-'+args.save.name)
        slots=repair(args.save,args.donor,output);print(f'Cópia criada: {output} ({len(slots)} slots recuperados)');return 0
    except (OSError,SaveError) as exc:
        print(f'Erro: {exc}',file=sys.stderr);return 1


if __name__=='__main__': raise SystemExit(main())
