"""Build a portable ZIP from an explicit allowlist, excluding all local data."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "KingdomsToolkit.ps1": ROOT / "portable/KingdomsToolkit.ps1",
    "1-Coletar-Diagnostico.cmd": ROOT / "portable/1-Coletar-Diagnostico.cmd",
    "2-Iniciar-Estavel.cmd": ROOT / "portable/2-Iniciar-Estavel.cmd",
    "3-Testar-Compatibilidade.cmd": ROOT / "portable/3-Testar-Compatibilidade.cmd",
    "4-Restaurar-Configuracao.cmd": ROOT / "portable/4-Restaurar-Configuracao.cmd",
    "5-Testar-D3D11-Sem-Async.cmd": ROOT / "portable/5-Testar-D3D11-Sem-Async.cmd",
    "6-Aplicar-Patch-Binario-NoAsync.cmd": ROOT / "portable/6-Aplicar-Patch-Binario-NoAsync.cmd",
    "7-Restaurar-Executavel-Original.cmd": ROOT / "portable/7-Restaurar-Executavel-Original.cmd",
    "LEIA-ME.txt": ROOT / "portable/LEIA-ME.txt",
    "startup-safe.json": ROOT / "profiles/startup-safe.json",
    "noasync-binary-patch.json": ROOT / "profiles/noasync-binary-patch.json",
    "RELATORIO.md": ROOT / "reports/diagnostico-inicial.md",
    "ANALISE-BINARIA-v2.md": ROOT / "reports/analise-binaria-v2.md",
    "VALIDACAO-v2.md": ROOT / "reports/validacao-v2.md",
    "rea-provenance.json": ROOT / "reports/rea-provenance.json",
    "native-provenance.json": ROOT / "reports/native-provenance.json",
}


def build():
    destination = ROOT / "dist/KingdomsReborn-GTX1080-Toolkit-v2.zip"
    destination.parent.mkdir(exist_ok=True)
    hashes = {}
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, source in FILES.items():
            raw = source.read_bytes()
            # CMD files need Windows line endings regardless of checkout settings.
            if name.endswith(".cmd"):
                raw = raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            archive.writestr("KingdomsReborn-Toolkit/" + name, raw)
            hashes[name] = hashlib.sha256(raw).hexdigest()
        archive.writestr("KingdomsReborn-Toolkit/manifest-sha256.json", json.dumps(hashes, indent=2))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip():
            raise RuntimeError("ZIP integrity check failed")
        assert len(archive.namelist()) == len(FILES) + 1
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".sha256.txt").write_text(f"{checksum}  {destination.name}\n", encoding="ascii")
    print(json.dumps({"path": str(destination), "bytes": destination.stat().st_size, "sha256": checksum}))
    return destination


if __name__ == "__main__":
    build()
