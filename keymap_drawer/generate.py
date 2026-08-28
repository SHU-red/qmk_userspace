#!/usr/bin/env python3
"""Render every keymap in this userspace to an SVG diagram.

Dependencies (installed by the CI workflow, or manually):
  - keymap-drawer  ->  pip install keymap-drawer
  - QMK CLI        ->  pip install qmk (subcommands load from the qmk_firmware checkout)
  - a qmk_firmware checkout containing the boards, pointed to by $QMK_HOME

Usage:
  QMK_HOME=/path/to/qmk_firmware python keymap_drawer/generate.py
"""

import json
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

# Pretty layer labels for keymaps that use numeric layer indices ([0], [1], ...)
# instead of named layers. Keyed by (board, keymap folder).
FIXED_LAYER_NAMES = {
    ("bastardkb/scylla", "vendor"): ["Base", "Symbols", "Function"],
    ("bastardkb/skeletyl", "shur3d"): ["Base", "Symbols", "Media/Nav", "RGB/Fn"],
    ("bastardkb/tbkmini", "vendor"): ["Base", "Numerals", "Symbols", "RGB"],
    ("bastardkb/tbkmini", "vendor"): ["Base", "Numerals", "Symbols", "RGB"],
}


def run(cmd, **kwargs):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def discover_keymaps():
    """Yield (board, keymap_name, keymap_c_path) for every keymap.c under keyboards/bastardkb."""
    found = []
    for keymap_c in KEYMAPS_ROOT.rglob("keymap.c"):
        parts = keymap_c.relative_to(KEYMAPS_ROOT).parts
        keymaps_idx = parts.index("keymaps")
        board = "/".join(("bastardkb", *parts[:keymaps_idx]))
        keymap_name = parts[keymaps_idx + 1]
        found.append((board, keymap_name, keymap_c))
    return sorted(found)


def layer_tokens_from_enum(keymap_c: str):
    """Extract real layer names in enum order from a QMK keymap.c (raw LAYER_* names)."""
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
    keymaps = discover_keymaps()
    if not keymaps:
        sys.exit(f"no keymaps found under {KEYMAPS_ROOT}")
    print(f"found {len(keymaps)} keymaps", flush=True)

    try:
        import cairosvg
    except ImportError:
        cairosvg = None

    for board, keymap_name, keymap_c in keymaps:
        keymap_src = keymap_c.read_text()

        # `qmk c2json` only accepts boards that ship keyboard.json. Boards
        # still using info.json get an equivalent keyboard.json synthesized in
        # the (throwaway) QMK checkout — same content, new file name.
        board_dir = qmk_home / "keyboards" / board
        keyboard_json = board_dir / "keyboard.json"
        if not keyboard_json.exists() and (board_dir / "info.json").exists():
            shutil.copy(board_dir / "info.json", keyboard_json)

        # keymaps that only exist in the userspace repo (e.g. shur3d) must be
        # mirrored into the QMK checkout or `qmk c2json` rejects them.
        qmk_keymap_dir = board_dir / "keymaps" / keymap_name
        if not qmk_keymap_dir.exists():
            shutil.copytree(keymap_c.parent, qmk_keymap_dir)

        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            keymap_json_path = td / "keymap.json"
            keymap_yaml = td / "keymap.yaml"

            # Some keymaps include headers c2json's preprocessor cannot resolve
            # (e.g. keymap_german.h); retry without cpp — c2json still expands
            # LAYOUT macros itself, so output is equivalent.
            c2json_cmd = ["qmk", "c2json", "-kb", board, "-km", keymap_name, keymap_c, "-o", keymap_json_path]
            try:
                run(c2json_cmd, env={**os.environ, "QMK_HOME": str(qmk_home)})
            except subprocess.CalledProcessError:
                run([*c2json_cmd[:2], "--no-cpp", *c2json_cmd[2:]], env={**os.environ, "QMK_HOME": str(qmk_home)})

            # c2json keeps named layer tokens (e.g. "LT(LAYER_POINTER, KC_Z)"),
            # but the keymap-drawer parser only understands numeric indices.
            text = keymap_json_path.read_text()
            layer_tokens = layer_tokens_from_enum(keymap_src)
            if layer_tokens:
                for idx, name in enumerate(layer_tokens):
                    text = re.sub(rf"\b{name}(?=[,)])", str(idx), text)
            keymap_json_path.write_text(text)

            layer_labels = FIXED_LAYER_NAMES.get((board, keymap_name))
            if layer_labels is None and layer_tokens:
                layer_labels = [pretty(name) for name in layer_tokens]
            if layer_labels is None:
                n_layers = len(json.loads(text)["layers"])
                layer_labels = [f"Layer {i}" for i in range(n_layers)]

            run(["keymap", "parse", "-q", keymap_json_path, "--layer-names", *layer_labels, "-o", keymap_yaml])
            out_svg = OUT_DIR / f"{board.replace('/', '_')}_{keymap_name}.svg"
            run(["keymap", "draw", keymap_yaml, "-o", out_svg])
            print(f"  -> {out_svg}", flush=True)
            if cairosvg is not None:
                out_png = out_svg.with_suffix(".png")
                cairosvg.svg2png(url=str(out_svg), write_to=str(out_png), scale=2)
                print(f"  -> {out_png}", flush=True)


if __name__ == "__main__":
    main()
