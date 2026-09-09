#!/usr/bin/env python3
"""Generate boilerplate directory structure + starter XML for a new JDE object.

Output matches the "extracted PAR" layout used by par_pack.py — a `specs/`
directory that `par_pack.py pack` will zip into `specs.zip`, so the normal
flow is:

    python scaffold.py <TYPE> <NAME> [options]
    # ... fill in the generated XML with real column/event-rule detail ...
    python validate_par.py <NAME>/
    python xml_transform.py add-bom <NAME>/specs/
    python par_pack.py pack <NAME>/ <NAME>.par

This produces STRUCTURE, not a finished object — every generated file is a
minimal, schema-correct skeleton (see references/core-rules.md and
references/par-file-structure.md) that still needs its real column
definitions, event rule logic, or form controls filled in by hand.

Usage:
    python scaffold.py TBLE F5500001 --prefix CU --system 55 --desc "Custom Table"
    python scaffold.py BSVW V5500001 --table F5500001 --system 55
    python scaffold.py DSTR D5500001 --type BSFN --system 55
    python scaffold.py DSTR T5500001 --type PO --system 55
    python scaffold.py BSFN_C B5500001 --ds D5500001 --system 55
    python scaffold.py BSFN_NER N5500001 --ds D5500001 --system 55
    python scaffold.py APPL P5500001 --system 55 --po T5500001 --view V5500001
"""
import os
import sys
import uuid
import datetime
import argparse

NS = 'xmlns="http://peoplesoft.com/e1/metadata/v1.0"'
NS_XS = 'xmlns:xs="http://www.w3.org/2001/XMLSchema"'
NS_ET = 'xmlns:et="http://peoplesoft.com/e1/metadata/v1.0/erptypes"'
FULL_NS = f'{NS}\n            {NS_XS}\n            {NS_ET}'


def _julian_today() -> str:
    """CYYDDD Julian date used in SIUPMJ (see config.py's own decoding rule)."""
    today = datetime.date.today()
    century = 1 if today.year >= 2000 else 0
    yy = today.year % 100
    day_of_year = today.timetuple().tm_yday
    return f"{century}{yy:02d}{day_of_year:03d}"


def _write(path: str, content: str, encoding: str = "utf-8") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding=encoding, newline="\n") as f:
        f.write(content)


def _write_inner_manifest(dir_path: str, obj_name: str, files: list) -> None:
    """manifest.xml — UTF-16 per the encoding rules. Written with a UTF-16 BOM."""
    filelist = "\n".join(f"    <file filename='{f}' id='{f}'/>" for f in files)
    xml = (
        "<?xml version='1.0' encoding='UTF-16' ?>\n"
        f"<manifest name='{_type_prefix(obj_name)}_{obj_name}' type='60' hosttype='99' release='E920'>\n"
        "  <filelist>\n"
        f"{filelist}\n"
        "  </filelist>\n"
        "</manifest>\n"
    )
    path = os.path.join(dir_path, "manifest.xml")
    with open(path, "wb") as f:
        f.write(b"\xff\xfe")
        f.write(xml.encode("utf-16-le"))


def _type_prefix(obj_name: str) -> str:
    # Best-effort inner-PAR TYPE segment from the object name's own prefix letter.
    return {
        "F": "TBLE", "V": "BSVW", "B": "BSFN", "N": "BSFN",
        "D": "DSTR", "T": "DSTR", "P": "APPL", "R": "APPL",
    }.get(obj_name[0].upper(), "OBJT")


def _f9860(siobnm: str, simd: str, sisy: str, sifuno: str, sifunu: str,
           sipfx: str = "  ", sisrclng: str = "   ", simid1: str = "") -> str:
    return (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<table name="F9860">\n'
        "  <row>\n"
        f'    <col name="SIOBNM">{siobnm:<10}</col>\n'
        f'    <col name="SIMD">{simd:<60}</col>\n'
        f'    <col name="SISY">{sisy:<4}</col>\n'
        f'    <col name="SISYR">{sisy:<4}</col>\n'
        f'    <col name="SIFUNO">{sifuno}</col>\n'
        f'    <col name="SIFUNU">{sifunu}</col>\n'
        f'    <col name="SIPFX">{sipfx}</col>\n'
        f'    <col name="SISRCLNG">{sisrclng}</col>\n'
        f'    <col name="SIMID1">{simid1:<10}</col>\n'
        '    <col name="SIPID">SCAFFOLD  </col>\n'
        '    <col name="SIUSER">JDE       </col>\n'
        f'    <col name="SIUPMJ">{_julian_today()}</col>\n'
        "  </row>\n"
        "</table>\n"
    )


def _f9861(siobnm: str) -> str:
    return (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<table name="F9861">\n'
        "  <row>\n"
        f'    <col name="SIOBNM">{siobnm:<10}</col>\n'
        '    <col name="SIJDEVERS">E920      </col>\n'
        '    <col name="SISTCE">3</col>\n'
        '    <col name="SIMRGMOD">C</col>\n'
        '    <col name="SIMRGOPT">2</col>\n'
        "  </row>\n"
        "</table>\n"
    )


# ---------------------------------------------------------------------------
# TBLE
# ---------------------------------------------------------------------------

def scaffold_tble(args: argparse.Namespace, out_dir: str) -> None:
    name = args.object_name
    prefix = args.prefix or "XX"
    desc = args.desc or f"{name} — TODO: description"

    _write(os.path.join(out_dir, "F9860.xml"), _f9860(
        name, desc, args.system, "TBLE", "210", sipfx=prefix,
    ))
    _write(os.path.join(out_dir, "F9861.xml"), _f9861(name))
    _write(os.path.join(out_dir, "include", f"{name}.h"),
           f"/* TODO: C struct typedef for {name}, one field per DDCLMN column. */\n")

    example_col_xml = (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<table name="F98711">\n'
        "  <row>\n"
        f'    <col name="TDOBNM">{name}</col>\n'
        '    <col name="TDOBND">AN8</col>\n'  # example DD alias — replace/add more columns
        f'    <col name="TDSQLC">{prefix}AN8</col>\n'
        '    <col name="TDPSEQ">1</col>\n'
        "  </row>\n"
        "</table>\n"
    )
    _write(os.path.join(out_dir, "specs", "DDCLMN", f"{name}.AN8.xml"), example_col_xml)
    os.makedirs(os.path.join(out_dir, "specs", "GBRSPEC"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "specs", "GBRLINK"), exist_ok=True)

    _write_inner_manifest(out_dir, name, [
        "F9860.xml", "F9861.xml", "specs.zip", f"include/{name}.h",
    ])
    print(f"NOTE: DDCLMN has one example column (AN8). Add one file per real column, "
          f"named '{name}.<DDAlias>.xml', with TDSQLC = '{prefix}' + the DD alias.")


# ---------------------------------------------------------------------------
# BSVW
# ---------------------------------------------------------------------------

def scaffold_bsvw(args: argparse.Namespace, out_dir: str) -> None:
    name = args.object_name
    table = args.table
    if not table:
        raise SystemExit("BSVW requires --table <TBLE object name>")
    desc = args.desc or f"{name} — TODO: description"

    _write(os.path.join(out_dir, "F9860.xml"), _f9860(name, desc, args.system, "BSVW", "300"))
    _write(os.path.join(out_dir, "F9861.xml"), _f9861(name))
    _write(os.path.join(out_dir, "include", f"BV{name}.h"),
           f"/* TODO: C struct typedef mirroring {name}'s Bob_ColumnCollection. */\n")

    busview_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<BSVW szView="{name}" szTable="{table}"\n'
        f'      szDescription="{desc}"\n'
        f'      {FULL_NS}>\n'
        "  <Bob_TableCollection>\n"
        f'    <Bob_Table idPrimaryIndex="1" szTable="{table}"/>\n'
        "  </Bob_TableCollection>\n"
        "  <DbrefCollection>\n"
        f'    <et:Dbref szTable="{table}" szDict="AN8"/>  <!-- TODO: real key column -->\n'
        "  </DbrefCollection>\n"
        "  <Bob_ColumnCollection>\n"
        f'    <Bob_Column iFlags="1" nSeq="0" szTable="{table}" szDict="AN8"/>  <!-- TODO: add every real column -->\n'
        "  </Bob_ColumnCollection>\n"
        "</BSVW>\n"
    )
    _write(os.path.join(out_dir, "specs", "BUSVIEW", f"{name}.xml"), busview_xml)

    _write_inner_manifest(out_dir, name, [
        "F9860.xml", "F9861.xml", "specs.zip", f"include/BV{name}.h",
    ])


# ---------------------------------------------------------------------------
# DSTR (BSFN or PO)
# ---------------------------------------------------------------------------

def scaffold_dstr(args: argparse.Namespace, out_dir: str) -> None:
    name = args.object_name
    ds_type = args.type
    if ds_type not in ("BSFN", "PO"):
        raise SystemExit("DSTR requires --type BSFN or --type PO")
    desc = args.desc or f"{name} — TODO: description"
    sifunu = "320" if ds_type == "BSFN" else "360"

    _write(os.path.join(out_dir, "F9860.xml"), _f9860(name, desc, args.system, "DSTR", sifunu))
    _write(os.path.join(out_dir, "F9861.xml"), _f9861(name))

    if ds_type == "BSFN":
        dstmpl_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<DSTemplate szTmplName="{name}" TemplateType="BSFN" nVersData="0"\n'
            f'            {FULL_NS}>\n'
            "  <DSTemplateDetails>\n"
            '    <DSTemplateDetail ItemID="1" DisplaySequence="1" CopyWord="EMPTY"\n'
            '                      DDAlias="AN8" FieldName="mnAddressNumber"\n'
            '                      LengthInVersData="50"/>  <!-- TODO: real parameters -->\n'
            "  </DSTemplateDetails>\n"
            "</DSTemplate>\n"
        )
        _write(os.path.join(out_dir, "specs", "DSTMPL", f"{name}.xml"), dstmpl_xml)
        _write_inner_manifest(out_dir, name, ["F9860.xml", "F9861.xml", "specs.zip"])
    else:
        dstmpl_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            f'<DSTemplate szTmplName="{name}" TemplateType="PO" nVersData="0"\n'
            f'            {FULL_NS}>\n'
            "  <DSTemplateDetails>\n"
            '    <DSTemplateDetail ItemID="1" PageNumber="1" DisplaySequence="0"\n'
            '                      CopyWord="EMPTY" DDAlias="AT1" FieldName="IT_TODO"\n'
            '                      LengthInVersData="8"/>  <!-- TODO: real PO parameters -->\n'
            "  </DSTemplateDetails>\n"
            "  <DSPageTitles>\n"
            '    <DSPageTitle PageNumber="1" ShortTitleTextID="0" PageTitleTextID="0"/>\n'
            "  </DSPageTitles>\n"
            "</DSTemplate>\n"
        )
        _write(os.path.join(out_dir, "specs", "DSTMPL", f"{name}.xml"), dstmpl_xml)

        potext_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<table name="F98306">\n'
            "  <row>\n"
            f'    <col name="PTOBNM">{name}</col>\n'
            '    <col name="PTPOTP">1</col>\n'
            '    <col name="PTITNUM">0</col>\n'
            '    <col name="PTSQNUM">0</col>\n'
            '    <col name="PTLNGP"></col>\n'
            "    <col name=\"PTPOTX\">TODO: processing option help text</col>\n"
            "  </row>\n"
            "</table>\n"
        )
        _write(os.path.join(out_dir, "specs", "POTEXT", f"{name}.1.0.0..xml"), potext_xml)
        _write_inner_manifest(out_dir, name, ["F9860.xml", "F9861.xml", "specs.zip"])


# ---------------------------------------------------------------------------
# BSFN_C
# ---------------------------------------------------------------------------

def scaffold_bsfn_c(args: argparse.Namespace, out_dir: str) -> None:
    name = args.object_name
    ds = args.ds
    if not ds:
        raise SystemExit("BSFN_C requires --ds <DSTR object name>")
    desc = args.desc or f"{name} — TODO: description"
    func_name = args.func_name or f"{name}Function"

    _write(os.path.join(out_dir, "F9860.xml"), _f9860(name, desc, args.system, "BSFN", "310", sisrclng="C"))
    _write(os.path.join(out_dir, "F9861.xml"), _f9861(name))

    f9862 = (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<table name="F9862">\n'
        "  <row>\n"
        f'    <col name="SIOBNM">{name:<10}</col>\n'
        f'    <col name="SIFCTNM">{func_name:<32}</col>\n'
        f'    <col name="SIMD">{desc:<40}</col>\n'
        f'    <col name="SIDSTNM">{ds:<10}</col>\n'
        '    <col name="SIEVSK">                                    </col>\n'
        '    <col name="SIBUF1">XXX</col>\n'
        '    <col name="SIBUF2">XXX</col>\n'
        "  </row>\n"
        "</table>\n"
    )
    _write(os.path.join(out_dir, "F9862.xml"), f9862)
    _write(os.path.join(out_dir, "F9863.xml"),
           '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<table name="F9863"></table>\n'
           "<!-- TODO: add a <row> per related table this function touches. -->\n")

    _write(os.path.join(out_dir, "include", f"{name}.h"), f"/* TODO: header for {func_name} */\n")
    _write(os.path.join(out_dir, "source", f"{name}.c"),
           f"/* {func_name} — TODO: implement.\n"
           f" * Data structure: {ds}\n */\n")

    busfunc_xml = (
        f'<BSFN szFcnName="{func_name}"\n'
        f'      szSourceFileName="{name}"\n'
        '      cSibflocn="2"\n'
        '      szAuthor="SCAFFOLD"\n'
        f'      szFcnBriefDesc="{desc}"\n'
        f'      SystemCode="{args.system}"\n'
        f'      szDsTmplName="{ds}"\n'
        '      wOrdinal="0"\n'
        f'      {NS}/>\n'
    )
    _write(os.path.join(out_dir, "specs", "BUSFUNC", f"{func_name}.xml"), busfunc_xml)

    _write_inner_manifest(out_dir, name, [
        "F9860.xml", "F9861.xml", "F9862.xml", "F9863.xml",
        "specs.zip", f"include/{name}.h", f"source/{name}.c",
    ])


# ---------------------------------------------------------------------------
# BSFN_NER
# ---------------------------------------------------------------------------

def scaffold_bsfn_ner(args: argparse.Namespace, out_dir: str) -> None:
    name = args.object_name
    ds = args.ds
    if not ds:
        raise SystemExit("BSFN_NER requires --ds <DSTR object name>")
    desc = args.desc or f"{name} — TODO: description"
    func_name = args.func_name or f"{name}Function"
    guid = str(uuid.uuid4())

    _write(os.path.join(out_dir, "F9860.xml"), _f9860(name, desc, args.system, "BSFN", "310", sisrclng="NER"))
    _write(os.path.join(out_dir, "F9861.xml"), _f9861(name))

    f9862 = (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        '<table name="F9862">\n'
        "  <row>\n"
        f'    <col name="SIOBNM">{name:<10}</col>\n'
        f'    <col name="SIFCTNM">{func_name:<32}</col>\n'
        f'    <col name="SIMD">{desc:<40}</col>\n'
        f'    <col name="SIDSTNM">{ds:<10}</col>\n'
        f'    <col name="SIEVSK">{guid}</col>\n'
        "  </row>\n"
        "</table>\n"
    )
    _write(os.path.join(out_dir, "F9862.xml"), f9862)
    _write(os.path.join(out_dir, "F9863.xml"),
           '<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<table name="F9863"></table>\n')

    busfunc_xml = (
        f'<BSFN szFcnName="{func_name}"\n'
        '      szSourceFileName="CFIN"\n'
        '      cSibflocn="1"\n'
        f'      szAuthor="{name}"\n'
        f'      szFcnBriefDesc="{desc}"\n'
        f'      SystemCode="{args.system}"\n'
        f'      szDsTmplName="{ds}"\n'
        '      wOrdinal="0"/>\n'
    )
    _write(os.path.join(out_dir, "specs", "BUSFUNC", f"{func_name}.xml"), busfunc_xml)

    gbrspec_xml = (
        f'<GBRSPEC szLastChangeTime="0" szLastChangeUser="SCAFFOLD"\n'
        f'         {FULL_NS}>\n'
        "  <!-- TODO: event rule statements go here — see references/par-file-structure.md Section 5 -->\n"
        "</GBRSPEC>\n"
    )
    _write(os.path.join(out_dir, "specs", "GBRSPEC", f"{guid}.xml"), gbrspec_xml)

    _write_inner_manifest(out_dir, name, ["F9860.xml", "F9861.xml", "F9862.xml", "F9863.xml", "specs.zip"])
    print(f"NOTE: F9862.SIEVSK is set to {guid} — this MUST match the GBRSPEC filename exactly; "
          f"don't rename one without the other (see core-rules.md rule 5).")


# ---------------------------------------------------------------------------
# APPL
# ---------------------------------------------------------------------------

def scaffold_appl(args: argparse.Namespace, out_dir: str) -> None:
    name = args.object_name
    po = args.po
    view = args.view
    if not po or not view:
        raise SystemExit("APPL requires --po <DSTR/PO object name> and --view <BSVW object name>")
    desc = args.desc or f"{name} — TODO: description"
    form = args.form or f"W{name[1:]}A"

    _write(os.path.join(out_dir, "F9860.xml"), _f9860(name, desc, args.system, "APPL", "164", simid1=po))
    _write(os.path.join(out_dir, "F9861.xml"), _f9861(name))

    f9865 = (
        '<table name="F9865">\n'
        "  <row>\n"
        f'    <col name="SWFMNM">{form}</col>\n'
        f'    <col name="SWMD">{desc}</col>\n'
        '    <col name="SWFMPT">FI</col>\n'
        '    <col name="SWENTRYPT">1</col>\n'
        f'    <col name="SWOBNM">{name}</col>\n'
        f'    <col name="SWSY">{args.system:<4}</col>\n'
        "  </row>\n"
        "</table>\n"
    )
    _write(os.path.join(out_dir, "F9865.xml"), f9865)

    fda_appl = (
        f'<FDA ApplicationName="{name}" {NS}>\n'
        "  <FDARecord>\n"
        f'    <FDAApplication TextId="2000" NextTextId="2001"\n'
        f'                    ProcessingOptionTemplate="{po}"/>\n'
        "  </FDARecord>\n"
        "</FDA>\n"
    )
    _write(os.path.join(out_dir, "specs", "FDASPEC", f"{name}.1..0.0.0.xml"), fda_appl)

    fda_form = (
        "<FDARecord>\n"
        f'  <FDAForm FormName="{form}"\n'
        f'           BusinessViewName="{view}"\n'
        '           FormType="FIX_INSPECT"\n'
        '           Width="604" Height="230"\n'
        '           FormTitleId="2000"\n'
        '           NextObjectId="1"/>  <!-- TODO: add controls, increment NextObjectId -->\n'
        "</FDARecord>\n"
    )
    _write(os.path.join(out_dir, "specs", "FDASPEC", f"{name}.2.{form}.0.0.0.xml"), fda_form)

    fda_text = (
        f'<FDAText ApplicationName="{name}" TextId="2000" {NS}>\n'
        f"{desc}\n"
        "</FDAText>\n"
    )
    _write(os.path.join(out_dir, "specs", "FDATEXT", f"{name}.2000.  .xml"), fda_text)

    os.makedirs(os.path.join(out_dir, "specs", "GBRLINK"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "specs", "GBRSPEC"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "specs", "DSTMPL"), exist_ok=True)

    svrhdr = f'<ASVRHeader ApplicationName="{name}"\n            ProcessingOptionTemplateName="{po}"/>\n'
    _write(os.path.join(out_dir, "specs", "SVRHDR", f"{name}.xml"), svrhdr)

    svrdtl = (
        f'<ASVRDetail ApplicationName="{name}"\n'
        f'            FormName="{form}"\n'
        f'            FormInterconnectTemplateName="{form}"/>\n'
    )
    _write(os.path.join(out_dir, "specs", "SVRDTL", f"{name}.{form}.xml"), svrdtl)

    _write_inner_manifest(out_dir, name, ["F9860.xml", "F9861.xml", "F9865.xml", "specs.zip"])
    print(f"NOTE: generated one starter form ({form}) with no controls yet — this is a skeleton, "
          f"not a working screen. Add FDASPEC type-3 controls, GBRLINK/GBRSPEC event rules, "
          f"and additional forms as needed (see references/par-file-structure.md Section 4.7).")


DISPATCH = {
    "TBLE": scaffold_tble,
    "BSVW": scaffold_bsvw,
    "DSTR": scaffold_dstr,
    "BSFN_C": scaffold_bsfn_c,
    "BSFN_NER": scaffold_bsfn_ner,
    "APPL": scaffold_appl,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("object_type", choices=sorted(DISPATCH.keys()))
    parser.add_argument("object_name")
    parser.add_argument("--system", default="55", help="System code, e.g. 55 (custom range is 55-59)")
    parser.add_argument("--desc", default=None, help="Object description")
    parser.add_argument("--prefix", default=None, help="TBLE: SQL column prefix, e.g. CU")
    parser.add_argument("--table", default=None, help="BSVW: the TBLE object this view is built on")
    parser.add_argument("--type", choices=["BSFN", "PO"], default=None, help="DSTR: BSFN data structure or PO (processing option) data structure")
    parser.add_argument("--ds", default=None, help="BSFN_C/BSFN_NER: the DSTR object this function's data structure")
    parser.add_argument("--func-name", default=None, help="BSFN_C/BSFN_NER: the real C/NER function name (default: <object>Function)")
    parser.add_argument("--po", default=None, help="APPL: the DSTR/PO object for this app's processing options")
    parser.add_argument("--view", default=None, help="APPL: the BSVW object the entry form is built on")
    parser.add_argument("--form", default=None, help="APPL: entry form name (default: W<name-without-P>A)")
    parser.add_argument("--out", default=None, help="Output directory (default: ./<object_name>)")

    args = parser.parse_args()
    out_dir = args.out or args.object_name
    if os.path.exists(out_dir) and os.listdir(out_dir):
        print(f"REFUSED: output directory '{out_dir}' already exists and is not empty.", file=sys.stderr)
        return 1

    DISPATCH[args.object_type](args, out_dir)
    print(f"Scaffolded {args.object_type} '{args.object_name}' in '{out_dir}/'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
