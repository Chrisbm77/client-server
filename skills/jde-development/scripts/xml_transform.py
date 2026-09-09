#!/usr/bin/env python3
"""XML encoding utilities for JDE PAR spec files.

See references/core-rules.md rule 8 and par-file-structure.md Section 1.3
for the encoding rules this script implements:

  - manifest.xml    : UTF-16, with BOM, XML declaration says encoding='UTF-16'
  - F98xx.xml       : plain UTF-8
  - all other specs : "dual-encoded" - a UTF-16 BOM + a UTF-16 mirror of the
                       content, immediately followed by the real UTF-8-encoded
                       XML (declaration + body). A parser that understands
                       this format skips past the UTF-16 portion to the UTF-8
                       XML declaration and reads from there.

Usage:
    python xml_transform.py prettify <path>              # dir or single file
    python xml_transform.py strip-bom <path>              # dir or single file
    python xml_transform.py add-bom <path>                # dir or single file
    python xml_transform.py manifest-to-utf8 <manifest.xml>
    python xml_transform.py manifest-to-utf16 <manifest.xml>
"""
import os
import re
import sys
import argparse
import xml.dom.minidom as minidom

UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"

# Matches a UTF-8 XML declaration as raw bytes, e.g. b'<?xml version="1.0" encoding="UTF-8"'
_UTF8_DECL_RE = re.compile(rb'<\?xml[^>]*encoding=[\'"]UTF-8[\'"][^>]*\?>')


def _iter_xml_files(path: str):
    if os.path.isfile(path):
        yield path
        return
    for root, _dirs, files in os.walk(path):
        for name in files:
            if name.lower().endswith(".xml"):
                yield os.path.join(root, name)


# ---------------------------------------------------------------------------
# strip-bom / add-bom — the dual-encoding transform
# ---------------------------------------------------------------------------

def _strip_bom_one(path: str) -> bool:
    with open(path, "rb") as f:
        raw = f.read()

    if not (raw.startswith(UTF16_LE_BOM) or raw.startswith(UTF16_BE_BOM)):
        return False  # already plain — nothing to strip

    match = _UTF8_DECL_RE.search(raw)
    if not match:
        print(f"  WARNING: {path} has a UTF-16 BOM but no UTF-8 declaration was found after it — left untouched.",
              file=sys.stderr)
        return False

    utf8_portion = raw[match.start():]
    with open(path, "wb") as f:
        f.write(utf8_portion)
    return True


def cmd_strip_bom(args: argparse.Namespace) -> int:
    changed = 0
    for path in _iter_xml_files(args.path):
        if _strip_bom_one(path):
            changed += 1
    print(f"strip-bom: {changed} file(s) converted to plain UTF-8.")
    return 0


def _add_bom_one(path: str) -> bool:
    with open(path, "rb") as f:
        raw = f.read()

    if raw.startswith(UTF16_LE_BOM) or raw.startswith(UTF16_BE_BOM):
        return False  # already dual-encoded — nothing to do

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        print(f"  WARNING: {path} is not valid UTF-8 — left untouched.", file=sys.stderr)
        return False

    mirror = text.encode("utf-16-le")
    with open(path, "wb") as f:
        f.write(UTF16_LE_BOM)
        f.write(mirror)
        f.write(raw)  # original UTF-8 declaration + body, unchanged
    return True


def cmd_add_bom(args: argparse.Namespace) -> int:
    changed = 0
    for path in _iter_xml_files(args.path):
        if _add_bom_one(path):
            changed += 1
    print(f"add-bom: {changed} file(s) given the dual-encoding prefix.")
    return 0


# ---------------------------------------------------------------------------
# prettify — assumes plain UTF-8 (run strip-bom first per the documented
# workflow in core-rules.md if a file still carries the dual-encoding prefix)
# ---------------------------------------------------------------------------

def _prettify_one(path: str) -> bool:
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(UTF16_LE_BOM) or raw.startswith(UTF16_BE_BOM):
        print(f"  SKIPPED: {path} is still dual-encoded — run strip-bom first.", file=sys.stderr)
        return False
    try:
        text = raw.decode("utf-8")
        dom = minidom.parseString(text)
    except Exception as e:
        print(f"  SKIPPED: {path} could not be parsed as XML ({e}).", file=sys.stderr)
        return False

    pretty_bytes = dom.toprettyxml(indent="  ", encoding="UTF-8")
    pretty = pretty_bytes.decode("utf-8")
    # minidom adds a redundant blank-line-heavy layout; collapse empty lines.
    pretty = "\n".join(line for line in pretty.splitlines() if line.strip())
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(pretty + "\n")
    return True


def cmd_prettify(args: argparse.Namespace) -> int:
    changed = 0
    for path in _iter_xml_files(args.path):
        if _prettify_one(path):
            changed += 1
    print(f"prettify: {changed} file(s) reformatted.")
    return 0


# ---------------------------------------------------------------------------
# manifest-to-utf8 / manifest-to-utf16
# ---------------------------------------------------------------------------

def cmd_manifest_to_utf8(args: argparse.Namespace) -> int:
    with open(args.manifest_file, "rb") as f:
        raw = f.read()
    if raw.startswith(UTF16_LE_BOM):
        text = raw[len(UTF16_LE_BOM):].decode("utf-16-le")
    elif raw.startswith(UTF16_BE_BOM):
        text = raw[len(UTF16_BE_BOM):].decode("utf-16-be")
    else:
        print("manifest is already not UTF-16 (no BOM found) — left untouched.")
        return 0
    text = text.replace("encoding='UTF-16'", "encoding='UTF-8'").replace('encoding="UTF-16"', 'encoding="UTF-8"')
    with open(args.manifest_file, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"Converted '{args.manifest_file}' to UTF-8.")
    return 0


def cmd_manifest_to_utf16(args: argparse.Namespace) -> int:
    with open(args.manifest_file, "rb") as f:
        raw = f.read()
    if raw.startswith(UTF16_LE_BOM) or raw.startswith(UTF16_BE_BOM):
        print("manifest is already UTF-16 — left untouched.")
        return 0
    text = raw.decode("utf-8")
    text = text.replace("encoding='UTF-8'", "encoding='UTF-16'").replace('encoding="UTF-8"', 'encoding="UTF-16"')
    with open(args.manifest_file, "wb") as f:
        f.write(UTF16_LE_BOM)
        f.write(text.encode("utf-16-le"))
    print(f"Converted '{args.manifest_file}' to UTF-16 (required for a real JDE manifest.xml).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("prettify", help="Pretty-print all XMLs in a directory (in-place)")
    p1.add_argument("path")
    p1.set_defaults(func=cmd_prettify)

    p2 = sub.add_parser("strip-bom", help="Strip UTF-16 BOM/mirror prefix from spec XMLs (for easier editing)")
    p2.add_argument("path")
    p2.set_defaults(func=cmd_strip_bom)

    p3 = sub.add_parser("add-bom", help="Restore UTF-16 BOM/mirror prefix (required before packaging)")
    p3.add_argument("path")
    p3.set_defaults(func=cmd_add_bom)

    p4 = sub.add_parser("manifest-to-utf8", help="Convert a manifest.xml from UTF-16 to UTF-8 (for editing)")
    p4.add_argument("manifest_file")
    p4.set_defaults(func=cmd_manifest_to_utf8)

    p5 = sub.add_parser("manifest-to-utf16", help="Convert a manifest.xml from UTF-8 back to UTF-16 (required for packaging)")
    p5.add_argument("manifest_file")
    p5.set_defaults(func=cmd_manifest_to_utf16)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
