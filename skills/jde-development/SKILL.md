---
name: jde-development
description: >
  JDE EnterpriseOne 9.2 development skill for creating, modifying, and managing
  JDE objects via PAR files (XML-based package format). Use this skill whenever
  the user asks about JDE development, JDE objects, PAR files, EnterpriseOne
  object creation or modification, or any task involving JDE tables, business
  views, data structures, business functions (C or NER), applications, event
  rules, form design, report design, or data dictionary items. Also trigger when
  the user mentions object types by their JDE names (F-tables, V-views, B/N-BSFNs,
  D-data structures, P-applications, T-processing options, R-reports) or wants
  to export, import, scaffold, validate, or transform JDE PAR files. This skill
  covers the full JDE development lifecycle — from understanding object
  relationships to generating production-ready PAR files.
---

# JDE EnterpriseOne 9.2 Development Skill

## Overview

This skill enables Claude to develop JDE EnterpriseOne 9.2 objects by working
with PAR files — the XML-based package format that JDE uses to export/import
development objects. PAR files convert JDE's internal BLOB-stored specs into
human-readable, programmatically manipulable XML.

The skill's reference documents are NOT stored on this machine — they're
fetched live from a vendor-hosted service, one topic at a time, only when
actually needed for the current task. This requires network access and a
valid API key (see Setup below).

## Setup (one-time)

This skill needs two environment variables set wherever Claude Code runs:
```
JDE_API_URL = <the URL your vendor gave you>
JDE_API_KEY = <the API key your vendor gave you>
```
If a fetch below returns a `CONFIGURATION ERROR`, `ACCESS ERROR`, or
`CONNECTION ERROR`, stop and resolve that before continuing — don't guess
at JDE conventions without the reference content.

## How This Skill Works

1. **Always start with the core rules** — run
   `python scripts/fetch_reference.py core-rules` before any other step.
   This covers naming conventions, object prefixes, and the rules that
   apply to every task regardless of object type.
2. **Identify the task type** from the decision guide below.
3. **Fetch the relevant reference topics** (and only those) using
   `scripts/fetch_reference.py <topic>` — each call retrieves that topic's
   full reference document as text.
4. **Use helper scripts** from `scripts/` for PAR file operations (these
   run entirely locally — no network needed).
5. **Follow JDE naming conventions and constraints** from the fetched
   references.

## Decision Guide — Which Reference Topics to Fetch

Before starting work, identify the task and fetch the minimum set of topics.

### Creating or Modifying a Table (F-prefix)
```
Fetch: python scripts/fetch_reference.py par-file-structure   (Section 4.3: TBLE)
Fetch: python scripts/fetch_reference.py table-design
Fetch: python scripts/fetch_reference.py data-dictionary       (for column DD aliases)
Script: python scripts/scaffold.py TBLE F55xxxx
```

### Creating or Modifying a Business View (V-prefix)
```
Fetch: python scripts/fetch_reference.py par-file-structure   (Section 4.4: BSVW)
Fetch: python scripts/fetch_reference.py business-view-design
Script: python scripts/scaffold.py BSVW V55xxxx
```

### Creating or Modifying a Data Structure (D-prefix or T-prefix)
```
Fetch: python scripts/fetch_reference.py par-file-structure   (Section 4.1-4.2: DSTR)
Fetch: python scripts/fetch_reference.py data-structure-design
Script: python scripts/scaffold.py DSTR D55xxxx    # BSFN DS
Script: python scripts/scaffold.py DSTR T55xxxx    # Processing Option DS
```

### Creating or Modifying a Business Function — C (B-prefix)
```
Fetch: python scripts/fetch_reference.py par-file-structure   (Section 4.5: BSFN C)
Fetch: python scripts/fetch_reference.py business-function-programming
Fetch: python scripts/fetch_reference.py data-structure-design   (for the DS)
Script: python scripts/scaffold.py BSFN_C B55xxxx
```

### Creating or Modifying a Business Function — NER (N-prefix)
```
Fetch: python scripts/fetch_reference.py par-file-structure   (Section 4.6: BSFN NER)
Fetch: python scripts/fetch_reference.py event-rules
Fetch: python scripts/fetch_reference.py data-structure-design   (for the DS)
Script: python scripts/scaffold.py BSFN_NER N55xxxx
```

### Creating or Modifying an Application (P-prefix)
```
Fetch: python scripts/fetch_reference.py par-file-structure   (Section 4.7: APPL)
Fetch: python scripts/fetch_reference.py application-design
Fetch: python scripts/fetch_reference.py form-design-aid
Fetch: python scripts/fetch_reference.py event-rules   (for GBRSPEC logic)
Script: python scripts/scaffold.py APPL P55xxxx
```

### Creating or Modifying a Report/UBE (R-prefix)
```
Fetch: python scripts/fetch_reference.py report-design-aid
Fetch: python scripts/fetch_reference.py event-rules   (for report event rules)
```

### Understanding Object Relationships / Architecture Questions
```
Fetch: python scripts/fetch_reference.py master-reference
Fetch: python scripts/fetch_reference.py par-file-structure   (Section 6: Cross-Object Reference Map)
```

### Working with PAR Files (extract, package, validate)
```
Fetch: python scripts/fetch_reference.py par-file-structure
Script: python scripts/par_pack.py extract <file.par> <output_dir>
Script: python scripts/par_pack.py pack <input_dir> <output.par>
Script: python scripts/validate_par.py <path>
Script: python scripts/xml_transform.py <action> <path>
```

### Data Dictionary Questions
```
Fetch: python scripts/fetch_reference.py data-dictionary
```

### Development Tools / Environment Questions
```
Fetch: python scripts/fetch_reference.py development-tools-overview
```

## Reference Topics Index

| Topic | Covers |
|-------|--------|
| `core-rules` | Naming conventions, object prefixes, and rules that apply to every task — always fetch first |
| `par-file-structure` | PAR ZIP architecture, all XML schemas, cross-object references, templates |
| `master-reference` | Unified development guide: architecture, naming, relationships, workflow |
| `table-design` | Table creation, indices, triggers, column design |
| `business-view-design` | View creation, joins, column selection, security |
| `data-dictionary` | DD items, aliases, data types, edit rules, UDCs |
| `data-structure-design` | BSFN and PO data structures, parameters, templates |
| `event-rules` | ER logic, variables, conditions, BSFN calls, DB I/O |
| `form-design-aid` | Form types, controls, grids, interconnects, events |
| `report-design-aid` | Report sections, data selection, runtime, batch |
| `application-design` | App architecture, form flow, processing options |
| `business-function-programming` | C and NER BSFNs, APIs, error handling, DLLs |
| `development-tools-overview` | OMW, OCM, UTB, deployment pipeline |

## Helper Scripts

All scripts are in `scripts/` and require Python 3.6+. `fetch_reference.py`
additionally requires the `requests` package and network access; the other
four run fully offline.

### fetch_reference.py — Reference Content Retrieval
```bash
python scripts/fetch_reference.py core-rules
python scripts/fetch_reference.py table-design
```

### par_pack.py — PAR Packaging and Extraction
```bash
# Extract a PAR file (handles nested ZIPs automatically)
python scripts/par_pack.py extract input.par output_dir/

# Repackage a directory into a valid PAR file
python scripts/par_pack.py pack input_dir/ output.par

# Extract only the outer level (don't recurse into inner PARs)
python scripts/par_pack.py extract input.par output_dir/ --no-recurse

# List contents without extracting
python scripts/par_pack.py list input.par
```

### scaffold.py — Object Scaffolding
```bash
# Generate complete boilerplate for a new object
python scripts/scaffold.py TBLE F5500001 --prefix CU --system 55 --desc "Custom Table"
python scripts/scaffold.py BSVW V5500001 --table F5500001 --system 55
python scripts/scaffold.py DSTR D5500001 --type BSFN --system 55
python scripts/scaffold.py DSTR T5500001 --type PO --system 55
python scripts/scaffold.py BSFN_C B5500001 --ds D5500001 --system 55
python scripts/scaffold.py BSFN_NER N5500001 --ds D5500001 --system 55
python scripts/scaffold.py APPL P5500001 --system 55 --po T5500001 --view V5500001

# Output is a ready-to-fill directory structure with all required XMLs
```

### validate_par.py — PAR Validation
```bash
# Validate an extracted PAR directory
python scripts/validate_par.py path/to/extracted/

# Validate a .par file directly (extracts to temp, validates, cleans up)
python scripts/validate_par.py file.par

# Verbose output showing all checks
python scripts/validate_par.py path/ --verbose
```

### xml_transform.py — XML Utilities
```bash
# Pretty-print all XMLs in a directory (in-place)
python scripts/xml_transform.py prettify path/to/extracted/

# Strip UTF-16 BOM prefix from spec XMLs (for easier editing)
python scripts/xml_transform.py strip-bom path/to/specs/

# Restore UTF-16 BOM prefix (for PAR-ready packaging)
python scripts/xml_transform.py add-bom path/to/specs/

# Convert manifest between UTF-16 and UTF-8
python scripts/xml_transform.py manifest-to-utf8 manifest.xml
python scripts/xml_transform.py manifest-to-utf16 manifest.xml
```

## Rules and Workflow Steps

Fetch `core-rules` (step 1 above) for the full list of naming conventions,
object prefixes, and the standard create/modify workflows — that content
lives there now rather than being duplicated in this file.
