#!/usr/bin/env python3
"""Documentation consistency checks for the FMP document set.

Checks:
  1. Every ID family is declared exactly once per ID in its registry document.
  2. Every ID referenced anywhere in the docs is declared.
  3. IDs declared but never referenced outside their registry file are reported
     as warnings (not failures).
  4. The immutable directive still matches the recorded SHA-256.

Exit code 0 means no errors. Warnings never fail the check.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ID family -> registry document that must declare it.
REGISTRY_FILES = {
    "INV": "docs/fmp-v0/01_contract.md",
    "EC": "docs/fmp-v0/02_encoding_choices.md",
    "E": "docs/fmp-v0/04_errors.md",
    "OD": "docs/fmp-v0/05_open_decisions.md",
    "N": "docs/fmp-v0/06_validation_matrix.md",
    "EXP": "docs/fmp-v0/06_validation_matrix.md",
    "AC": "docs/fmp-v0/06_validation_matrix.md",
    # HE-1 (`ADR-0125`): the design document's §3 and §14 tables are the single
    # declaration site for the acceptance and test IDs. Registered here from H0
    # so a reference cannot name an acceptance item that does not exist.
    "HE-AC": "docs/architecture/he1-horizontal-extension.md",
    "HE-T": "docs/architecture/he1-horizontal-extension.md",
}

# ID family -> token pattern.
PATTERNS = {
    "INV": r"INV-\d{2}",
    "EC": r"EC-\d{2}",
    "E": r"E-[A-Z]+-\d{3}",
    "OD": r"OD-\d{2}",
    "N": r"N\d{2}",
    "EXP": r"EXP-R\d+",
    "AC": r"AC-\d{2}",
    "HE-AC": r"HE-AC-\d{2}",
    "HE-T": r"HE-T\d{2}",
}

DIRECTIVE = "docs/fmp-v0/00_directive.md"
SOURCE_INDEX = "research/evidence/source_index.md"

# Catalogue families are allowed to be self-contained in their registry doc.
CATALOGUE_FAMILIES = {"EC", "E", "HE-AC", "HE-T"}


def family_of(identifier: str) -> str:
    """The longest registered family that prefixes `identifier`.

    `HE-T01` has no separator before its number, so the family cannot be derived
    by splitting on `-`; the registered spellings are authoritative.
    """
    best = None
    for family in REGISTRY_FILES:
        if not identifier.startswith(family):
            continue
        rest = identifier[len(family) :]
        if rest.isdigit() or (rest.startswith("-") and rest[1:].isdigit()):
            if best is None or len(family) > len(best):
                best = family
    if best is not None:
        return best
    return identifier.split("-")[0] if "-" in identifier else identifier.rstrip("0123456789")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def doc_files():
    files = [ROOT / "README.md", ROOT / "AGENTS.md"]
    docs = ROOT / "docs"
    if docs.is_dir():
        files.extend(sorted(docs.rglob("*.md")))
    return [f for f in files if f.is_file()]


def collect_declarations(errors):
    """Return id -> [(file, line)] for every registry row."""
    declarations = {}
    for family, relative in REGISTRY_FILES.items():
        path = ROOT / relative
        if not path.is_file():
            errors.append("registry file missing: %s" % relative)
            continue
        text = read(path)
        row = re.compile(r"^\s*\|\s*(" + PATTERNS[family] + r")\s*\|", re.MULTILINE)
        for match in row.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            declarations.setdefault(match.group(1), []).append((relative, line))
    return declarations


def collect_references():
    """Return id -> set of files that mention it."""
    references = {}
    for family, pattern in PATTERNS.items():
        token = re.compile(
            r"(?<![0-9A-Za-z_-])(" + pattern + r")(?![0-9A-Za-z_-])"
        )
        for path in doc_files():
            text = read(path)
            for match in token.finditer(text):
                references.setdefault(match.group(1), set()).add(rel(path))
    return references


def check_directive(errors, warnings):
    directive = ROOT / DIRECTIVE
    index = ROOT / SOURCE_INDEX
    if not directive.is_file():
        errors.append("missing immutable directive: %s" % DIRECTIVE)
        return
    if not index.is_file():
        warnings.append("no source index; directive checksum not verified")
        return
    match = re.search(r"directive_sha256:\s*([0-9a-f]{64})", read(index))
    if not match:
        warnings.append("directive_sha256 not recorded in %s" % SOURCE_INDEX)
        return
    actual = hashlib.sha256(directive.read_bytes()).hexdigest()
    if match.group(1) != actual:
        errors.append(
            "directive checksum mismatch: recorded %s, actual %s"
            % (match.group(1), actual)
        )


def main() -> int:
    errors = []
    warnings = []

    declarations = collect_declarations(errors)
    references = collect_references()

    for identifier in sorted(declarations):
        locations = declarations[identifier]
        if len(locations) > 1:
            where = ", ".join("%s:%d" % item for item in locations)
            errors.append("duplicate declaration of %s at %s" % (identifier, where))

    for identifier in sorted(references):
        if identifier not in declarations:
            where = ", ".join(sorted(references[identifier]))
            errors.append("reference to undeclared %s in %s" % (identifier, where))

    registry_of = {}
    for family, relative in REGISTRY_FILES.items():
        registry_of[family] = relative

    for identifier in sorted(declarations):
        family = family_of(identifier)
        if family in CATALOGUE_FAMILIES:
            continue
        own = registry_of.get(family)
        outside = references.get(identifier, set()) - {own}
        if own and not outside:
            warnings.append(
                "%s is declared but not referenced outside %s" % (identifier, own)
            )

    check_directive(errors, warnings)

    counts = {}
    for identifier in declarations:
        family = family_of(identifier)
        counts[family] = counts.get(family, 0) + 1

    print("declared:", ", ".join("%s=%d" % (k, counts[k]) for k in sorted(counts)))
    shown = 0
    for warning in warnings:
        if shown >= 20:
            print("warning: ... and %d more" % (len(warnings) - shown))
            break
        print("warning: %s" % warning)
        shown += 1
    for error in errors:
        print("error: %s" % error)

    if errors:
        print("FAIL (%d error(s), %d warning(s))" % (len(errors), len(warnings)))
        return 1
    print("OK (%d warning(s))" % len(warnings))
    return 0


if __name__ == "__main__":
    sys.exit(main())
