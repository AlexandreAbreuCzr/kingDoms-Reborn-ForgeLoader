"""Compatibility entry point for the ForgeLoader Dev Kit download builder."""
import json
from pathlib import Path
from build_releases import build as build_release

ROOT = Path(__file__).resolve().parents[1]


def build():
    output = build_release(devkit_only=True)
    config = json.loads((ROOT / 'release.json').read_text())
    return output / config['devkit_archive']


if __name__ == '__main__': build()
