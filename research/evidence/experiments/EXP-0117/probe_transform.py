#!/usr/bin/env python3
"""Probe what the materializer does when `adr` carries `adrp`'s transform.

`ADR-0118` claims two separate things, and only one of them is enforced:

- the absent page *row* (`aarch64:adr/x64-imm21-page`) is `E-FORM-001`
  (`N01ff`), and the `0.18.0` boundary is `E-FORM-001` (`N01fg`);
- the *transform* is not compared with the mnemonic. This script measures that
  second statement instead of inferring it from a function name.

It copies the committed `A64-P23` plan, sets the first fixup to
`pcrel_page` + `page`, and materializes it twice:

1. as committed (section has no `base_address`) — the page rule needs the
   target's address, so the plan is `E-FIXUP-002`;
2. with `base_address: 0` — the plan is accepted and emits bytes, even though
   the row is `adr` and the transform is the page one. Here the two values
   happen to agree (site 20 and symbol 20 are on page 0), which is exactly why
   this is a contract gap and not a diagnostic: a non-zero page delta would
   emit the byte encoding of a page count.

Usage (from the repository root, after `cargo build -p fmp-cli`):

    python research/evidence/experiments/EXP-0117/probe_transform.py
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PLAN = ROOT / "fixtures/aarch64/positive/A64-P23-adr-imm21.fmp.json"
DEFINITIONS = ROOT / "definitions"


def cli() -> Path:
    for candidate in (ROOT / "prototype/target/debug/fmp.exe",
                      ROOT / "prototype/target/debug/fmp"):
        if candidate.exists():
            return candidate
    raise SystemExit("build the CLI first: prototype/target/debug/fmp")


def materialize(plan: dict) -> tuple:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "probe.json"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(plan, indent=2) + "\n")
        result = subprocess.run(
            [str(cli()), "materialize", str(path), "--definitions",
             str(DEFINITIONS)],
            capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def committed_bytes() -> str:
    with PLAN.open(encoding="utf-8") as handle:
        code, out, err = materialize(json.load(handle))
    if code != 0:
        raise SystemExit("committed plan rejected: %s" % err.strip())
    return json.loads(out)["bytes_hex"]


def main() -> int:
    expected = committed_bytes()
    with PLAN.open(encoding="utf-8") as handle:
        probe = json.load(handle)
    probe["fixups"][0]["pc_reference_rule"] = "pcrel_page"
    probe["fixups"][0]["value_transform"] = "page"

    code, out, err = materialize(probe)
    print("without base_address: exit %d" % code)
    if code != 1 or "E-FIXUP-002" not in err:
        raise SystemExit("expected E-FIXUP-002 without a base address: %s"
                         % err.strip())
    print("  E-FIXUP-002 (the page rule needs the target's address)")

    probe["sections"][0]["base_address"] = 0
    code, out, err = materialize(probe)
    print("with base_address 0: exit %d" % code)
    if code != 0:
        raise SystemExit("expected acceptance, got %s" % err.strip())
    artifact = json.loads(out)
    print("  bytes %s" % artifact["bytes_hex"])
    print("  identical to the identity plan: %s"
          % (artifact["bytes_hex"] == expected))
    print("")
    print("So `adr` + `page` is accepted: the encoder does not compare the")
    print("transform with the mnemonic, and the written record is the only")
    print("statement of intent. `E-FIXUP-002` came from the missing address,")
    print("not from the mismatch. Here the page delta is 0, so the bytes")
    print("coincide; a non-zero delta would encode a page count as bytes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
