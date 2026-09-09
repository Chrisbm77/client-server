#!/usr/bin/env python3
"""Pack, extract, and list JDE PAR files.

A PAR file is a nested ZIP archive (see references/par-file-structure.md,
Section 1.1): an outer .par can contain inner .par files, and any inner
PAR can contain a specs.zip. This tool walks that nesting automatically
in both directions:

  extract  - unzips a .par, and recursively unzips any nested *.par or
             specs.zip found inside it, into plain directories.
  pack     - reverses that: zips any directory back into specs.zip if it's
             named "specs", or into <dirname>.par if its name matches the
             inner-PAR naming convention {TYPE}_{NAME}_{PKG}_{HOST}.
  list     - shows the contents of a .par (and its nested archives)
             without extracting anything to disk.

Usage:
    python par_pack.py extract <file.par> <output_dir> [--no-recurse]
    python par_pack.py pack <input_dir> <output.par>
    python par_pack.py list <file.par>
"""
import os
import re
import sys
import shutil
import zipfile
import argparse

INNER_PAR_NAME_RE = re.compile(r"^(APPL|TBLE|BSVW|BSFN|DSTR)_[A-Za-z0-9]+_\d+_\d+$")


def _is_nested_archive_name(filename: str) -> bool:
    return filename.lower().endswith(".par") or filename.lower() == "specs.zip"


def _extract_zip(zip_path: str, dest_dir: str, recurse: bool) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)

    if not recurse:
        return

    # Walk the freshly extracted tree looking for nested archives to expand
    # in place, replacing each nested archive file with a directory of the
    # same base name (minus its extension).
    for root, _dirs, files in os.walk(dest_dir):
        for name in list(files):
            if not _is_nested_archive_name(name):
                continue
            nested_path = os.path.join(root, name)
            if name.lower() == "specs.zip":
                nested_dest = os.path.join(root, "specs")
            else:
                nested_dest = os.path.join(root, name[:-4])  # strip ".par"
            _extract_zip(nested_path, nested_dest, recurse=True)
            os.remove(nested_path)


def cmd_extract(args: argparse.Namespace) -> int:
    if not os.path.exists(args.par_file):
        print(f"NOT FOUND: {args.par_file}", file=sys.stderr)
        return 1
    if os.path.exists(args.output_dir) and os.listdir(args.output_dir):
        print(f"REFUSED: output directory '{args.output_dir}' already exists and is not empty.", file=sys.stderr)
        return 1
    _extract_zip(args.par_file, args.output_dir, recurse=not args.no_recurse)
    print(f"Extracted '{args.par_file}' to '{args.output_dir}'"
          f"{' (outer level only)' if args.no_recurse else ' (recursively)'}.")
    return 0


def _zip_dir(src_dir: str, zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            rel_root = os.path.relpath(root, src_dir)
            # Preserve empty directories (e.g. GBRSPEC/GBRLINK with no table
            # triggers yet) as explicit zip entries — os.walk alone would
            # silently drop them since zipfile only stores what's written.
            if not files and not dirs and rel_root != ".":
                zf.writestr(rel_root.replace(os.sep, "/") + "/", "")
            for name in sorted(files):
                full_path = os.path.join(root, name)
                arcname = os.path.relpath(full_path, src_dir)
                # Use forward slashes inside the archive regardless of host OS.
                zf.write(full_path, arcname.replace(os.sep, "/"))


def _repack_nested_dirs(work_dir: str) -> None:
    """Bottom-up: turn any 'specs' directory into specs.zip, and any
    directory matching the inner-PAR naming convention into <name>.par,
    within their parent directory, then remove the now-repacked directory.
    """
    # Walk bottom-up so nested PARs-within-PARs collapse correctly.
    for root, dirs, _files in os.walk(work_dir, topdown=False):
        for d in list(dirs):
            full_dir = os.path.join(root, d)
            if d == "specs":
                target = os.path.join(root, "specs.zip")
                _zip_dir(full_dir, target)
                shutil.rmtree(full_dir)
            elif INNER_PAR_NAME_RE.match(d):
                target = os.path.join(root, d + ".par")
                _zip_dir(full_dir, target)
                shutil.rmtree(full_dir)


def cmd_pack(args: argparse.Namespace) -> int:
    if not os.path.isdir(args.input_dir):
        print(f"NOT FOUND: input directory '{args.input_dir}'", file=sys.stderr)
        return 1

    # Work on a throwaway copy so packing never mutates the user's source tree.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = os.path.join(tmp, "work")
        shutil.copytree(args.input_dir, work_dir)
        _repack_nested_dirs(work_dir)
        _zip_dir(work_dir, args.output_par)

    print(f"Packed '{args.input_dir}' into '{args.output_par}'.")
    return 0


def _list_zip(zip_path: str, prefix: str) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            print(f"{prefix}{info.filename}")
            if _is_nested_archive_name(info.filename):
                # Peek inside nested archives without extracting to disk.
                import io
                data = zf.read(info.filename)
                with zipfile.ZipFile(io.BytesIO(data)) as inner_zf:
                    for inner_info in inner_zf.infolist():
                        print(f"{prefix}  {info.filename} :: {inner_info.filename}")
                        if _is_nested_archive_name(inner_info.filename):
                            inner_data = inner_zf.read(inner_info.filename)
                            with zipfile.ZipFile(io.BytesIO(inner_data)) as inner2:
                                for i2 in inner2.infolist():
                                    print(f"{prefix}    {inner_info.filename} :: {i2.filename}")


def cmd_list(args: argparse.Namespace) -> int:
    if not os.path.exists(args.par_file):
        print(f"NOT FOUND: {args.par_file}", file=sys.stderr)
        return 1
    _list_zip(args.par_file, prefix="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="Extract a PAR file (handles nested ZIPs automatically)")
    p_extract.add_argument("par_file")
    p_extract.add_argument("output_dir")
    p_extract.add_argument("--no-recurse", action="store_true",
                            help="Extract only the outer level; leave nested .par/specs.zip files as-is.")
    p_extract.set_defaults(func=cmd_extract)

    p_pack = sub.add_parser("pack", help="Repackage a directory into a valid PAR file")
    p_pack.add_argument("input_dir")
    p_pack.add_argument("output_par")
    p_pack.set_defaults(func=cmd_pack)

    p_list = sub.add_parser("list", help="List contents without extracting")
    p_list.add_argument("par_file")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
