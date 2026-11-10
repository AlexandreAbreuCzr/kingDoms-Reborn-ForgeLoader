"""Generate the actual modified game EXE in dist, preserving the installed original."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(game: Path):
    spec = json.loads((ROOT / "profiles/noasync-binary-patch.json").read_text(encoding="utf-8"))
    source = game / spec["target_relative_path"]
    original = source.read_bytes()
    if len(original) != spec["size"] or hashlib.sha256(original).hexdigest() != spec["source_sha256"]:
        raise ValueError("Executavel original diferente da versao analisada; geracao recusada.")
    offset = spec["file_offset"]
    before = bytes.fromhex(spec["original_hex"])
    after = bytes.fromhex(spec["patched_hex"])
    if len(before) != len(after) or original[offset:offset + len(before)] != before:
        raise ValueError("Instrucoes originais inesperadas.")
    modified = original[:offset] + after + original[offset + len(before):]
    if hashlib.sha256(modified).hexdigest() != spec["patched_sha256"]:
        raise ValueError("Hash do EXE modificado incorreto.")
    changed = [i for i, (a, b) in enumerate(zip(original, modified)) if a != b]
    if changed != list(range(offset, offset + len(before))):
        raise ValueError("Alteracoes fora do intervalo autorizado.")

    package = ROOT / "dist/KingdomsReborn-EXE-Experimental"
    target = package / spec["target_relative_path"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != spec["patched_sha256"]:
        raise ValueError("Destino ja existe com conteudo diferente; arquivo preservado.")
    temporary = target.with_suffix(".exe.tmp")
    with temporary.open("xb") as stream:
        stream.write(modified)
    temporary.replace(target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == spec["patched_sha256"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == spec["source_sha256"]

    readme = """KINGDOMS REBORN - EXECUTAVEL MODIFICADO EXPERIMENTAL

Este pacote contem o EXE real do jogo modificado, nao um iniciador nem
um instalador de patch. Foi gerado do executavel fornecido no projeto.
Nao e uma recompilacao do codigo-fonte e nao e o jogo completo.

INSTALACAO NO PC DO PARCEIRO
1. Feche o jogo e use a mesma versao da pasta fornecida neste projeto.
2. Na pasta do jogo, abra PunCity\\Binaries\\Win64.
3. Copie o PrototypeCity-Win64-Shipping.exe original para um local de backup.
4. Copie o EXE deste pacote para essa mesma pasta, substituindo o original.
   Preserve o nome PrototypeCity-Win64-Shipping.exe.
5. Com o Steam aberto, inicie pelo KingdomsReborn.exe normal, na raiz do jogo.

O arquivo modificado precisa das DLLs e do conteudo da instalacao original.
Nao tente abrir o EXE sozinho na pasta Downloads, dentro deste ZIP ou na
pasta extraida deste pacote sem os arquivos do jogo.

PARA DESFAZER
Com o jogo fechado, recoloque o EXE original que voce guardou no passo 3.

ALTERACAO
A funcao D3D11RHI_ShouldAllowAsyncResourceCreation retorna false.
Isso fixa a mesma escolha que a opcao -nod3dasync, independentemente dos
argumentos do iniciador. Foram alterados somente quatro bytes.
Os verificadores de erro Direct3D e a deteccao de dispositivo perdido
continuam ativos. Saves, DLLs e licenciamento nao foram alterados.

Se -nod3dasync ja foi aplicado corretamente e falhou, este EXE nao oferece
uma hipotese diferente: ele fixa o mesmo resultado nessa funcao.

VALIDACAO E LIMITES
Os quatro bytes, os hashes e a preservacao do original foram conferidos.
O EXE modificado nao foi executado nesta etapa e ainda nao foi validado
na GTX 1080 do computador afetado. Nao ha garantia de resolver o crash.
Nao foi identificada uma causa comprovada para essa maquina.
Use somente com a versao correspondente aos hashes do manifesto.
"""
    (package / "LEIA-ME.txt").write_text(readme, encoding="utf-8")
    manifest = {
        "artifact": "modified-game-executable",
        "status": "experimental; not runtime validated",
        "relative_path": spec["target_relative_path"],
        "source_sha256": spec["source_sha256"],
        "modified_sha256": spec["patched_sha256"],
        "size": len(modified),
        "changed_byte_offsets": changed,
        "original_hex": spec["original_hex"],
        "modified_hex": spec["patched_hex"],
        "function": spec["function"],
        "not_a_source_rebuild": True,
        "installed_original_preserved": True,
        "modified_executable_executed": False,
    }
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    archive_path = package.with_suffix(".zip")
    members = [target, package / "LEIA-ME.txt", package / "manifest.json"]
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for member in members:
            archive.write(member, (Path(package.name) / member.relative_to(package)).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Falha de integridade no ZIP.")
        extracted = archive.read((Path(package.name) / target.relative_to(package)).as_posix())
        assert hashlib.sha256(extracted).hexdigest() == spec["patched_sha256"]
        assert len(archive.namelist()) == 3
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    archive_path.with_suffix(".sha256.txt").write_text(f"{checksum}  {archive_path.name}\n", encoding="ascii")
    result = {"exe": str(target), "exe_bytes": target.stat().st_size,
              "exe_sha256": spec["patched_sha256"], "zip": str(archive_path),
              "zip_bytes": archive_path.stat().st_size, "zip_sha256": checksum,
              "changed_bytes": len(changed), "installed_original_preserved": True}
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, default=Path.home() / "Downloads/Kingdoms Reborn")
    build(parser.parse_args().game)
