#!/usr/bin/env python3
"""Validate a JDE PAR object against the structural rules in
references/par-file-structure.md Section 9.4 ("Key Rules for Valid PAR
Files") and core-rules.md.

This checks internal consistency of what's on disk — it cannot confirm
that a referenced object (a DSTR, a BSVW) that lives *outside* the given
path actually exists in your JDE environment; those cross-PAR references
are reported as informational notes, not failures, unless the referenced
object is also present under the same root.

Usage:
    python validate_par.py path/to/extracted/
    python validate_par.py file.par              # extracted to a temp dir, validated, cleaned up
    python validate_par.py path/ --verbose
"""
import os
import re
import sys
import uuid
import shutil
import zipfile
import tempfile
import argparse
import xml.etree.ElementTree as ET

UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"
GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class Result:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.notes = []

    def ok(self, msg, verbose_only=False, verbose=False):
        self.passed += 1
        if verbose_only and not verbose:
            return
        print(f"  PASS: {msg}")

    def fail(self, msg):
        self.failed += 1
        print(f"  FAIL: {msg}")

    def note(self, msg):
        self.notes.append(msg)
        print(f"  NOTE: {msg}")


# ---------------------------------------------------------------------------
# Extraction helper (mirrors par_pack.py's recursive nested-zip handling,
# duplicated here so this script has no dependency on the others).
# ---------------------------------------------------------------------------

def _is_nested_archive_name(filename: str) -> bool:
    return filename.lower().endswith(".par") or filename.lower() == "specs.zip"


def _extract_zip(zip_path: str, dest_dir: str) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)
    for root, _dirs, files in os.walk(dest_dir):
        for name in list(files):
            if not _is_nested_archive_name(name):
                continue
            nested_path = os.path.join(root, name)
            nested_dest = os.path.join(root, "specs" if name.lower() == "specs.zip" else name[:-4])
            _extract_zip(nested_path, nested_dest)
            os.remove(nested_path)


def _read_xml_text(path: str) -> str:
    """Read an XML file regardless of which encoding stage it's in:
    plain UTF-8, UTF-16 (manifest.xml), or dual-encoded (BOM+mirror+UTF-8).
    """
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(UTF16_LE_BOM) or raw.startswith(UTF16_BE_BOM):
        match = re.search(rb'<\?xml[^>]*encoding=[\'"]UTF-8[\'"][^>]*\?>', raw)
        if match:
            return match.group(0)[0:0].join([raw[match.start():]]).decode("utf-8")
        # No embedded UTF-8 payload — this is a plain UTF-16 file (manifest.xml).
        body = raw[2:]
        try:
            return body.decode("utf-16-le")
        except UnicodeDecodeError:
            return body.decode("utf-16-be")
    return raw.decode("utf-8")


def _col(row_elem, name, default=""):
    for col in row_elem.findall("col"):
        if col.get("name") == name:
            return (col.text or "").strip()
    return default


def _f98xx_row(path):
    """Parse a simple <table><row><col name=...>value</col>...</row></table> file."""
    text = _read_xml_text(path)
    root = ET.fromstring(text)
    row = root.find("row")
    return row


# ---------------------------------------------------------------------------
# Per-object checks
# ---------------------------------------------------------------------------

def validate_object(obj_dir: str, verbose: bool) -> Result:
    r = Result()
    name = os.path.basename(obj_dir.rstrip("/"))
    print(f"\n=== {name} ({obj_dir}) ===")

    # -- Well-formedness of every XML file --------------------------------
    xml_files = []
    for root, _dirs, files in os.walk(obj_dir):
        for f in files:
            if f.lower().endswith(".xml"):
                xml_files.append(os.path.join(root, f))
    malformed = 0
    for path in xml_files:
        try:
            ET.fromstring(_read_xml_text(path))
        except ET.ParseError as e:
            r.fail(f"{os.path.relpath(path, obj_dir)} is not well-formed XML: {e}")
            malformed += 1
    if malformed == 0:
        r.ok(f"all {len(xml_files)} XML files are well-formed", verbose_only=True, verbose=verbose)

    # -- manifest.xml -------------------------------------------------------
    manifest_path = os.path.join(obj_dir, "manifest.xml")
    listed_files = []
    if not os.path.exists(manifest_path):
        r.fail("manifest.xml is missing")
    else:
        with open(manifest_path, "rb") as f:
            head = f.read(2)
        if head not in (UTF16_LE_BOM, UTF16_BE_BOM):
            r.fail("manifest.xml is not UTF-16 (no BOM found) — run xml_transform.py manifest-to-utf16")
        else:
            r.ok("manifest.xml is UTF-16 encoded", verbose_only=True, verbose=verbose)
        try:
            mroot = ET.fromstring(_read_xml_text(manifest_path))
            for file_el in mroot.findall(".//file"):
                listed_files.append(file_el.get("filename"))
        except ET.ParseError as e:
            r.fail(f"manifest.xml could not be parsed: {e}")

        for fname in listed_files:
            on_disk = os.path.join(obj_dir, fname)
            on_disk_expanded = on_disk[:-4] if fname.lower() == "specs.zip" else on_disk
            if fname.lower() == "specs.zip":
                on_disk_expanded = os.path.join(obj_dir, "specs")
            if not (os.path.exists(on_disk) or os.path.exists(on_disk_expanded)):
                r.fail(f"manifest.xml lists '{fname}' but it doesn't exist on disk")
        if listed_files:
            r.ok(f"all {len(listed_files)} files listed in manifest.xml exist on disk", verbose_only=True, verbose=verbose) \
                if all(os.path.exists(os.path.join(obj_dir, f)) or os.path.exists(os.path.join(obj_dir, "specs")) for f in listed_files) \
                else None

    # -- F9860 / F9861 name consistency -------------------------------------
    f9860_path = os.path.join(obj_dir, "F9860.xml")
    f9861_path = os.path.join(obj_dir, "F9861.xml")
    siobnm = sifuno = sifunu = sipfx = sisrclng = simid1 = None
    if not os.path.exists(f9860_path):
        r.fail("F9860.xml is missing")
    else:
        row = _f98xx_row(f9860_path)
        siobnm = _col(row, "SIOBNM")
        sifuno = _col(row, "SIFUNO")
        sifunu = _col(row, "SIFUNU")
        sipfx = _col(row, "SIPFX")
        sisrclng = _col(row, "SISRCLNG")
        simid1 = _col(row, "SIMID1")
        if siobnm != name:
            r.fail(f"F9860.SIOBNM ('{siobnm}') doesn't match the object directory name ('{name}')")
        else:
            r.ok("F9860.SIOBNM matches object name", verbose_only=True, verbose=verbose)

    if not os.path.exists(f9861_path):
        r.fail("F9861.xml is missing")
    else:
        row = _f98xx_row(f9861_path)
        f9861_siobnm = _col(row, "SIOBNM")
        if siobnm is not None and f9861_siobnm != siobnm:
            r.fail(f"F9861.SIOBNM ('{f9861_siobnm}') doesn't match F9860.SIOBNM ('{siobnm}')")
        else:
            r.ok("F9861.SIOBNM matches F9860.SIOBNM", verbose_only=True, verbose=verbose)

    # -- Type-specific checks -----------------------------------------------
    if sifuno == "BSFN":
        f9862_path = os.path.join(obj_dir, "F9862.xml")
        f9863_path = os.path.join(obj_dir, "F9863.xml")
        sievsk = ""
        if not os.path.exists(f9862_path):
            r.fail("F9862.xml is required for a BSFN object but is missing")
        else:
            row = _f98xx_row(f9862_path)
            f9862_siobnm = _col(row, "SIOBNM")
            sievsk = _col(row, "SIEVSK")
            sidstnm = _col(row, "SIDSTNM")
            if siobnm is not None and f9862_siobnm != siobnm:
                r.fail(f"F9862.SIOBNM ('{f9862_siobnm}') doesn't match F9860.SIOBNM ('{siobnm}')")
            if not sidstnm:
                r.fail("F9862.SIDSTNM (data structure link) is blank — every BSFN needs one")
            else:
                r.ok(f"F9862.SIDSTNM references '{sidstnm}'", verbose_only=True, verbose=verbose)
                r.note(f"'{sidstnm}' must exist as a real DSTR object — not verified here unless it's under the same root")

            if sisrclng == "NER":
                if not sievsk or not GUID_RE.match(sievsk):
                    r.fail("F9862.SIEVSK must be a GUID for a NER business function")
                else:
                    gbrspec_path = os.path.join(obj_dir, "specs", "GBRSPEC", f"{sievsk}.xml")
                    if not os.path.exists(gbrspec_path):
                        r.fail(f"F9862.SIEVSK is '{sievsk}' but specs/GBRSPEC/{sievsk}.xml doesn't exist")
                    else:
                        r.ok("F9862.SIEVSK matches an existing GBRSPEC file", verbose_only=True, verbose=verbose)
            elif sisrclng == "C":
                if sievsk.strip():
                    r.fail("F9862.SIEVSK should be blank for a C business function (SIEVSK is NER-only)")
                busfunc_dir = os.path.join(obj_dir, "specs", "BUSFUNC")
                if not os.path.isdir(busfunc_dir) or not os.listdir(busfunc_dir):
                    r.fail("specs/BUSFUNC/ is missing or empty for a C business function")

        if not os.path.exists(f9863_path):
            r.fail("F9863.xml is required for a BSFN object but is missing")
        elif sisrclng == "NER":
            text = _read_xml_text(f9863_path)
            if "<row>" in text:
                r.fail("F9863.xml should be empty for a NER (table relationships are embedded in GBRSPEC)")
            else:
                r.ok("F9863.xml is empty, as expected for a NER", verbose_only=True, verbose=verbose)

    elif sifuno == "TBLE":
        ddclmn_dir = os.path.join(obj_dir, "specs", "DDCLMN")
        if not os.path.isdir(ddclmn_dir) or not os.listdir(ddclmn_dir):
            r.fail("specs/DDCLMN/ is missing or empty — a table needs at least one column definition")
        else:
            bad = 0
            for fname in sorted(os.listdir(ddclmn_dir)):
                if not fname.lower().endswith(".xml"):
                    continue
                row = _f98xx_row(os.path.join(ddclmn_dir, fname))
                tdobnm = _col(row, "TDOBNM")
                tdobnd = _col(row, "TDOBND")
                tdsqlc = _col(row, "TDSQLC")
                if tdobnm != siobnm:
                    r.fail(f"{fname}: TDOBNM ('{tdobnm}') doesn't match this table's name ('{siobnm}')")
                    bad += 1
                expected = f"{(sipfx or '').strip()}{tdobnd}"
                if tdsqlc != expected:
                    r.fail(f"{fname}: TDSQLC ('{tdsqlc}') should be SIPFX+DDAlias ('{expected}')")
                    bad += 1
            if bad == 0:
                r.ok(f"all DDCLMN column names follow the {siobnm} SIPFX+DDAlias rule", verbose_only=True, verbose=verbose)

    elif sifuno == "APPL":
        f9865_path = os.path.join(obj_dir, "F9865.xml")
        if not os.path.exists(f9865_path):
            r.fail("F9865.xml (form directory) is required for an APPL object but is missing")
        if not simid1:
            r.note("F9860.SIMID1 (processing option template link) is blank — set it if this app has a PO template")
        fdaspec_dir = os.path.join(obj_dir, "specs", "FDASPEC")
        if not os.path.isdir(fdaspec_dir) or not os.listdir(fdaspec_dir):
            r.fail("specs/FDASPEC/ is missing or empty")

    # -- GBRLINK -> GBRSPEC consistency (applies to TBLE and APPL) ---------
    for gbrlink_dir, gbrspec_dir in _find_gbr_pairs(obj_dir):
        for fname in sorted(os.listdir(gbrlink_dir)):
            if not fname.lower().endswith(".xml"):
                continue
            root_el = ET.fromstring(_read_xml_text(os.path.join(gbrlink_dir, fname)))
            key = root_el.get("EventSpecKey")
            if not key:
                r.fail(f"{fname}: GBRLink has no EventSpecKey attribute")
                continue
            target = os.path.join(gbrspec_dir, f"{key}.xml")
            if not os.path.exists(target):
                r.fail(f"{fname}: EventSpecKey '{key}' has no matching file in {os.path.relpath(gbrspec_dir, obj_dir)}/")
        if os.path.isdir(gbrlink_dir) and os.listdir(gbrlink_dir):
            r.ok(f"all GBRLINK entries in {os.path.relpath(gbrlink_dir, obj_dir)}/ resolve to a GBRSPEC file",
                 verbose_only=True, verbose=verbose)

    return r


def _find_gbr_pairs(obj_dir: str):
    pairs = []
    for root, dirs, _files in os.walk(obj_dir):
        if os.path.basename(root) == "GBRLINK":
            sibling_gbrspec = os.path.join(os.path.dirname(root), "GBRSPEC")
            pairs.append((root, sibling_gbrspec))
    return pairs


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _find_object_dirs(root: str):
    if os.path.exists(os.path.join(root, "F9860.xml")):
        return [root]
    found = []
    for dirpath, _dirs, files in os.walk(root):
        if "F9860.xml" in files:
            found.append(dirpath)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"NOT FOUND: {args.path}", file=sys.stderr)
        return 1

    tmp_dir = None
    target = args.path
    if os.path.isfile(args.path):
        tmp_dir = tempfile.mkdtemp(prefix="validate_par_")
        _extract_zip(args.path, tmp_dir)
        target = tmp_dir

    try:
        object_dirs = _find_object_dirs(target)
        if not object_dirs:
            print("NOT FOUND: no F9860.xml found anywhere under this path — is this really a JDE object?", file=sys.stderr)
            return 1

        total_pass = total_fail = 0
        for obj_dir in object_dirs:
            r = validate_object(obj_dir, args.verbose)
            total_pass += r.passed
            total_fail += r.failed

        print(f"\n{'=' * 60}\n{total_pass} check(s) passed, {total_fail} failed, across {len(object_dirs)} object(s).")
        return 1 if total_fail else 0
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
