"""Local, reversible diagnostics for the supplied Kingdoms Reborn installation.

Python standard library only. Does not patch executables, drivers, registry or saves.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GAME = Path.home() / "Downloads" / "Kingdoms Reborn"
SAVED = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PunCity" / "Saved"
EXE = Path("PunCity/Binaries/Win64/PrototypeCity-Win64-Shipping.exe")
PROFILE = json.loads((ROOT / "profiles/startup-safe.json").read_text(encoding="utf-8"))


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def powershell(code):
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", code],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Falha ao consultar o Windows")
    return json.loads(result.stdout.strip().lstrip("\ufeff") or "null")


def running_game():
    if os.name != "nt":
        return []
    return powershell("@(Get-Process -Name 'PrototypeCity-Win64-Shipping','KingdomsReborn' "
                      "-ErrorAction SilentlyContinue | Select-Object Id,ProcessName) | ConvertTo-Json -Compress") or []


def require_closed():
    if running_game():
        raise RuntimeError("Feche o jogo antes de alterar/restaurar a configuracao.")


def update_ini(text, changes):
    """Preserve unrelated entries, comments and sections; update repeated keys too."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    output = []
    current = None
    seen = {}
    section_names = {key.casefold(): key for key in changes}

    def finish_section():
        if current in changes:
            missing = [(k, v) for k, v in changes[current].items() if k.casefold() not in seen[current]]
            if missing and output and not output[-1].endswith(("\n", "\r")):
                output[-1] += newline
            output.extend(f"{key}={value}{newline}" for key, value in missing)
            seen[current].update(key.casefold() for key, _ in missing)

    for line in lines:
        header = re.match(r"^\s*\[([^\]]+)\]\s*(?:[;#].*)?$", line.rstrip("\r\n"))
        if header:
            finish_section()
            current = section_names.get(header.group(1).casefold())
            if current:
                seen.setdefault(current, set())
        elif current:
            entry = re.match(r"^(\s*)([^=;#\s][^=]*?)(\s*)=(.*?)(\r?\n)?$", line)
            if entry:
                key = next((k for k in changes[current] if k.casefold() == entry.group(2).strip().casefold()), None)
                if key:
                    ending = entry.group(5) or ""
                    line = f"{entry.group(1)}{entry.group(2)}{entry.group(3)}={changes[current][key]}{ending}"
                    seen[current].add(key.casefold())
        output.append(line)
    finish_section()
    for section, keys in changes.items():
        if section not in seen:
            if output and not output[-1].endswith(("\n", "\r")):
                output[-1] += newline
            output.append(f"{newline}[{section}]{newline}")
            output.extend(f"{key}={value}{newline}" for key, value in keys.items())
    return "".join(output)


def edit_bytes(raw, changes):
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        text = raw.decode(encoding)
    except UnicodeDecodeError:
        encoding = "cp1252"
        text = raw.decode(encoding)
    return update_ini(text, changes).encode(encoding)


def atomic_write(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def apply_profile(saved, apply=False, backup_root=None):
    config = Path(saved).resolve() / "Config" / "WindowsNoEditor"
    planned = []
    for name, changes in PROFILE.items():
        path = config / name
        before = path.read_bytes() if path.exists() else b""
        after = edit_bytes(before, changes)
        if before != after:
            planned.append((path, before, after, path.exists()))
    if not apply:
        return {"applied": False, "files": [str(p) for p, *_ in planned], "profile": PROFILE}
    require_closed()
    if not planned:
        return {"applied": False, "reason": "O perfil ja esta aplicado; nenhum arquivo foi alterado."}
    backup_root = Path(backup_root or ROOT / "backups")
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=dt.datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=backup_root)).resolve()
    manifest = {"created_at": utc_now(), "config_directory": str(config), "files": [], "state": "prepared"}
    for path, before, after, existed in planned:
        if existed:
            (backup / path.name).write_bytes(before)
        manifest["files"].append({"name": path.name, "existed": existed,
                                  "before_sha256": hashlib.sha256(before).hexdigest(),
                                  "after_sha256": hashlib.sha256(after).hexdigest()})
    write_json(backup / "manifest.json", manifest)
    try:
        for path, before, after, existed in planned:
            # Refuse a concurrent edit between planning and writing.
            if path.exists() != existed or (existed and path.read_bytes() != before):
                raise RuntimeError(f"Configuracao mudou durante a aplicacao: {path}")
            atomic_write(path, after)
    except Exception:
        manifest["state"] = "partial; inspect before restoring"
        write_json(backup / "manifest.json", manifest)
        raise
    manifest["state"] = "applied"
    write_json(backup / "manifest.json", manifest)
    return {"applied": True, "backup": str(backup), "files": [str(p) for p, *_ in planned]}


def restore_profile(backup, saved, force=False):
    require_closed()
    backup = Path(backup).resolve()
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    config = Path(saved).resolve() / "Config" / "WindowsNoEditor"
    if config != Path(manifest["config_directory"]).resolve():
        raise ValueError("O backup pertence a outra pasta de configuracao.")
    for item in manifest["files"]:
        if item["name"] not in PROFILE:
            raise ValueError("Nome de arquivo inesperado no manifesto.")
        path = config / item["name"]
        if item["existed"] and digest(backup / item["name"]) != item["before_sha256"]:
            raise ValueError("Backup danificado; restauracao cancelada.")
        if not force and (not path.exists() or digest(path) != item["after_sha256"]):
            raise RuntimeError("Configuracao alterada depois do perfil; use --force somente apos revisar as diferencas.")
    # When forced, preserve all current files before replacing them.
    safety = Path(tempfile.mkdtemp(prefix="before-restore-", dir=backup))
    for item in manifest["files"]:
        path = config / item["name"]
        if path.exists():
            shutil.copy2(path, safety / item["name"])
        if item["existed"]:
            atomic_write(path, (backup / item["name"]).read_bytes())
        else:
            path.unlink(missing_ok=True)
    return {"restored": True, "preserved_current": str(safety)}


def crash_records(saved):
    records = []
    for path in sorted((Path(saved) / "Crashes").glob("*/CrashContext.runtime-xml")):
        try:
            tree = ET.parse(path)
            props = tree.find("RuntimeProperties")
            keys = ["EngineVersion", "BuildVersion", "SecondsSinceStart", "ErrorMessage", "CallStack",
                    "Misc.PrimaryGPUBrand", "Misc.CPUBrand", "MemoryStats.bIsOOM"]
            fields = {k: props.findtext(k) for k in keys} if props is not None else {}
            error = fields.get("ErrorMessage") or ""
            category = "d3d-device-lost" if "D3D device" in error else "startup-movie-window" if "FDefaultGameMoviePlayer" in (fields.get("CallStack") or "") else "other"
            records.append({"path": str(path), "modified_at": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat(),
                            "sha256": digest(path), "category": category, "properties": fields})
        except (ET.ParseError, OSError) as exc:
            records.append({"path": str(path), "error": str(exc)})
    return records


def pe_facts(path):
    """File-header observations and exact string presence, not decompilation."""
    data = path.read_bytes()
    if data[:2] != b"MZ":
        raise ValueError("Nao e um executavel PE")
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("Assinatura PE invalida")
    machine, count, stamp = struct.unpack_from("<HHI", data, pe + 4)
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    directories = optional + (112 if magic == 0x20b else 96)
    sections = []
    start = optional + optional_size
    for i in range(count):
        offset = start + 40 * i
        name = data[offset:offset + 8].rstrip(b"\0").decode("ascii", "replace")
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
        sections.append({"name": name, "rva": rva, "virtual_size": virtual_size, "raw_size": raw_size, "raw_offset": raw_offset})

    def file_offset(rva):
        for section in sections:
            delta = rva - section["rva"]
            if 0 <= delta < section["raw_size"]:
                return section["raw_offset"] + delta
        raise ValueError(f"RVA sem bytes em arquivo: {rva:#x}")

    def cstring(offset):
        end = data.find(b"\0", offset, offset + 1024)
        return data[offset:end].decode("ascii", "replace") if end >= 0 else "<unterminated>"

    imports = []
    import_rva, _ = struct.unpack_from("<II", data, directories + 8)
    if import_rva:
        offset = file_offset(import_rva)
        for i in range(512):
            descriptor = struct.unpack_from("<IIIII", data, offset + i * 20)
            if not any(descriptor):
                break
            imports.append(cstring(file_offset(descriptor[3])))
    needles = ["r.Streaming.LimitPoolSizeToVRAM", "t.MaxFPS", "r.TextureStreaming", "NoStartupMovies",
               "nostartupmovies", "DX11", "D3D11RHI", "D3D12RHI", "VulkanRHI", "SafeCreateTexture2D",
               "FDefaultGameMoviePlayer", "r.Streaming.PoolSize", "r.RHICmdBypass", "norhithread"]
    strings = {}
    for needle in needles:
        hits = []
        for encoding in ("ascii", "utf-16le"):
            position = data.find(needle.encode(encoding))
            if position >= 0:
                hits.append({"encoding": encoding, "file_offset": position})
        strings[needle] = hits
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
            "machine": hex(machine), "pe_magic": hex(magic), "coff_timestamp": stamp,
            "sections": sections, "imports": imports, "exact_string_hits": strings,
            "limitations": ["String presence does not establish a code path, command support or runtime value.",
                            "Import inventory excludes delay imports and dynamically loaded modules."]}


def compare_zip(game, archive):
    targets = ["KingdomsReborn.exe", EXE.as_posix(), "PunCity/Content/Paks/PunCity-WindowsNoEditor.pak"]
    rows = []
    with zipfile.ZipFile(archive) as z:
        for relative in targets:
            matches = [i for i in z.infolist() if i.filename.replace("\\", "/").endswith("/" + relative) or i.filename.replace("\\", "/") == relative]
            if len(matches) != 1:
                rows.append({"path": relative, "error": "Membro ausente ou ambiguo no ZIP"})
                continue
            member = matches[0]
            h = hashlib.sha256()
            with z.open(member) as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
            installed_hash = digest(game / relative)
            rows.append({"path": relative, "zip_member": member.filename, "zip_crc_verified": True,
                         "sha256_zip": h.hexdigest(), "sha256_installed": installed_hash,
                         "matches": h.hexdigest() == installed_hash})
    return {"archive": str(archive), "files": rows,
            "limitation": "Matching the supplied ZIP does not establish authenticity or correctness of that ZIP."}


def diagnose(game, saved):
    usage = shutil.disk_usage(game)
    hardware = powershell("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
        "[pscustomobject]@{gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate,AdapterRAM); "
        "cpu=@(Get-CimInstance Win32_Processor | Select-Object Name); "
        "ram=(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory} | ConvertTo-Json -Depth 5") if os.name == "nt" else None
    return {"collected_at": utc_now(), "game": str(game), "saved": str(saved), "hardware": hardware,
            "disk_free_bytes": usage.free, "crashes": crash_records(saved), "pe": pe_facts(game / EXE),
            "config_files": {n: {"exists": (saved / "Config/WindowsNoEditor" / n).exists(),
                                "sha256": digest(saved / "Config/WindowsNoEditor" / n) if (saved / "Config/WindowsNoEditor" / n).exists() else None}
                             for n in PROFILE},
            "limitations": ["No FPS, GPU memory, temperature or game stability measurements in this static report.",
                            "Win32_VideoController.AdapterRAM is a 32-bit field; do not infer RX 7600 VRAM capacity from it."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, default=GAME)
    parser.add_argument("--saved", type=Path, default=SAVED)
    commands = parser.add_subparsers(dest="command", required=True)
    diagnosis = commands.add_parser("diagnose")
    diagnosis.add_argument("--output", type=Path, default=ROOT / "artifacts/diagnosis.json")
    profile = commands.add_parser("profile")
    profile.add_argument("--apply", action="store_true", help="Sem esta opcao, apenas mostra o plano")
    restore = commands.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--force", action="store_true")
    integrity = commands.add_parser("verify-zip")
    integrity.add_argument("archive", type=Path)
    integrity.add_argument("--output", type=Path, default=ROOT / "artifacts/integrity.json")
    watch = commands.add_parser("watch")
    watch.add_argument("--seconds", type=int, default=120)
    watch.add_argument("--output", type=Path, default=ROOT / "artifacts/watch.json")
    args = parser.parse_args()
    if args.command == "diagnose":
        data = diagnose(args.game, args.saved)
        write_json(args.output, data)
        print(json.dumps({"output": str(args.output), "crashes": len(data["crashes"]), "exe_sha256": data["pe"]["sha256"]}))
    elif args.command == "profile":
        print(json.dumps(apply_profile(args.saved, args.apply), indent=2, ensure_ascii=False))
    elif args.command == "restore":
        print(json.dumps(restore_profile(args.backup, args.saved, args.force), indent=2, ensure_ascii=False))
    elif args.command == "verify-zip":
        data = compare_zip(args.game, args.archive)
        write_json(args.output, data)
        print(json.dumps(data, indent=2))
        if any(not item.get("matches") for item in data["files"]):
            return 2
    elif args.command == "watch":
        if args.seconds < 1:
            parser.error("--seconds deve ser positivo")
        baseline = {r["sha256"] for r in crash_records(args.saved) if "sha256" in r}
        samples = []
        started = time.monotonic()
        while time.monotonic() - started < args.seconds:
            samples.append({"at": utc_now(), "processes": running_game()})
            time.sleep(min(5, max(0, args.seconds - (time.monotonic() - started))))
        fresh = [r for r in crash_records(args.saved) if r.get("sha256") not in baseline]
        data = {"samples": samples, "new_crashes": fresh,
                "limitation": "Process presence is not evidence of a responsive menu or stable gameplay."}
        write_json(args.output, data)
        print(json.dumps({"output": str(args.output), "new_crashes": len(fresh)}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)
