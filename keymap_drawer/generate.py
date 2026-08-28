#!/usr/bin/env python3
"""Render every keymap in this userspace to an SVG diagram.

Dependencies (installed by the CI workflow, or manually):
  - keymap-drawer  ->  pip install keymap-drawer
  - QMK CLI        ->  pip install qmk (subcommands load from the qmk_firmware checkout)
  - a qmk_firmware checkout containing the boards, pointed to by $QMK_HOME

Usage:
  QMK_HOME=/path/to/qmk_firmware python keymap_drawer/generate.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYMAPS_ROOT = REPO_ROOT / "keyboards" / "bastardkb"
OUT_DIR = REPO_ROOT / "keymap_images"
EXTRA_LAYOUTS_DIR = Path(__file__).resolve().parent / "extra_layouts"

# board -> keymap folder relative to keyboards/bastardkb
BOARDS = {
    "bastardkb/charybdis/3x5": Path("charybdis/3x5"),
    "bastardkb/charybdis/3x6": Path("charybdis/3x6"),
    "bastardkb/charybdis/4x6": Path("charybdis/4x6"),
    "bastardkb/dilemma/3x5_2": Path("dilemma/3x5_2"),
    "bastardkb/dilemma/3x5_3": Path("dilemma/3x5_3"),
    "bastardkb/dilemma/4x6_4": Path("dilemma/4x6_4"),
    "bastardkb/scylla": Path("scylla"),
    "bastardkb/skeletyl": Path("skeletyl"),
    "bastardkb/tbkmini": Path("tbkmini"),
}

# Keymaps that use numeric layer indices ([0], [1], ...) instead of named layers.
FIXED_LAYER_NAMES = {
    "bastardkb/scylla": ["Base", "Symbols", "Function"],
    "bastardkb/skeletyl": ["Base", "Numerals", "Symbols", "RGB"],
    "bastardkb/tbkmini": ["Base", "Numerals", "Symbols", "RGB"],
}


def run(cmd, **kwargs):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def layer_names_from_enum(keymap_c: str):
    """Extract real layer names in enum order from a QMK keymap.c."""
    for block in re.findall(r"enum\s+\w*\s*\{([^}]*)\}", keymap_c):
        members = []
        idx = 0
        for line in block.splitlines():
            line = line.split("//")[0].strip().rstrip(",")
            m = re.match(r"(\w+)\s*(?:=\s*(\d+))?", line)
            if m:
                if m.group(2):
                    idx = int(m.group(2))
                members.append((m.group(1), idx))
                idx += 1
        layer_members = [name for name, _ in members if name.startswith("LAYER_")]
        used = set(re.findall(r"\[(LAYER_\w+)\]\s*=", keymap_c))
        layers = [n for n in layer_members if n in used]
        if layers:
            return layers
    return None


def pretty(name: str) -> str:
    parts = name.split("_", 1)
    words = parts[1] if len(parts) > 1 else parts[0]
    return " ".join(w if w.isupper() and len(w) <= 3 else w.capitalize() for w in words.split())


def main():
    qmk_home = Path(os.environ.get("QMK_HOME", ""))
    if not qmk_home.exists():
        sys.exit("QMK_HOME must point to a qmk_firmware checkout containing the bastardkb boards")

    # Install extra physical layouts into the keymap-drawer package so boards
    # without bundled geometry (dilemma/3x5_2) render correctly.
    import keymap_drawer

    extra_layouts_dst = Path(keymap_drawer.__file__).resolve().parent.parent / "resources" / "extra_layouts"
    extra_layouts_dst.mkdir(parents=True, exist_ok=True)
    for src in EXTRA_LAYOUTS_DIR.glob("*.json"):
        shutil.copy(src, extra_layouts_dst / src.name)

    OUT_DIR.mkdir(exist_ok=True)
    for board, rel in BOARDS.items():
        keymap_c = KEYMAPS_ROOT / rel / "keymaps" / "vendor" / "keymap.c"
        if not keymap_c.exists():
            print(f"!! {board}: keymap not found at {keymap_c}", flush=True)
            continue

        # `qmk c2json` only accepts boards that ship keyboard.json. Boards
        # still using info.json get an equivalent keyboard.json synthesized in
        # the (throwaway) QMK checkout — same content, new file name.
        board_dir = qmk_home / "keyboards" / board
        keyboard_json = board_dir / "keyboard.json"
        if not keyboard_json.exists() and (board_dir / "info.json").exists():
            shutil.copy(board_dir / "info.json", keyboard_json)

        layers = FIXED_LAYER_NAMES.get(board) or layer_names_from_enum(keymap_c.read_text())
        if not layers:
            print(f"!! {board}: could not determine layer names", flush=True)
            continue
        layer_labels = [pretty(name) for name in layers]

        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            keymap_json = td / "keymap.json"
            keymap_yaml = td / "keymap.yaml"

            run(
                ["qmk", "c2json", "-kb", board, "-km", "vendor", keymap_c, "-o", keymap_json],
                env={**os.environ, "QMK_HOME": str(qmk_home)},
            )

            # c2json keeps named layer tokens (e.g. "LT(LAYER_POINTER, KC_Z)"),
            # but the keymap-drawer parser only understands numeric indices.
            text = keymap_json.read_text()
            for idx, name in enumerate(layers):
                text = re.sub(rf"\b{name}(?=[,)])", str(idx), text)
            keymap_json.write_text(text)

            run(["keymap", "parse", "-q", keymap_json, "--layer-names", *layer_labels, "-o", keymap_yaml])
            out_svg = OUT_DIR / f"{board.replace('/', '_')}.svg"
            run(["keymap", "draw", keymap_yaml, "-o", out_svg])
            print(f"  -> {out_svg}", flush=True)


if __name__ == "__main__":
    main()
