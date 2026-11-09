#!/usr/bin/env python3
"""Measure the width split behind `0.68.0`'s per-form `requires_extensions`.

`probe.asm` names one operation, `vmovaps`, at three operand widths. The
encoding family and the width bits fall out of the bytes:

| source | family | bytes | width field |
|---|---|---|---|
| `vmovaps %xmm1, %xmm0` | VEX | `c5 f8 28 c1` | `L = 0` (128-bit) |
| `vmovaps %ymm1, %ymm0` | VEX | `c5 fc 28 c1` | `L = 1` (256-bit) |
| `vmovaps %zmm1, %zmm0` | EVEX | `62 f1 7c 48 28 c1` | `L'L = 10` (512-bit) |

`evex-widths.s` supplies the EVEX.128 and EVEX.256 byte strings, which the
assembler will not select, so `llvm-mc -disassemble` reads `L'L = 00/01`.

`mattr.txt` records the negative probe: `vmovaps` assembles with `-avx`,
`-avx512f` and `-avx512vl` switched off, so this toolchain has no per-mnemonic
extension gate to use as an oracle. The mapping from width bits to extension
names is therefore `inference` from the documented ISA, not a measured
rejection; `EXP-0104-*.md` says so.

Usage (from the repository root):

    python research/evidence/experiments/EXP-0104/measure.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROBE = HERE / "probe.asm"
EVEX_WIDTHS = HERE / "evex-widths.s"

EXPECTED = bytes.fromhex(
    "c5f828c1"        # vmovaps %xmm1, %xmm0   VEX.128
    "c5fc28c1"        # vmovaps %ymm1, %ymm0   VEX.256
    "62f17c4828c1"    # vmovaps %zmm1, %zmm0   EVEX.512
)

# The assembler must accept each of these even though the named extension is
# switched off; a non-zero rc would mean a gating oracle exists after all.
MATTR_CASES = [
    ("avx-off", "-mattr=-avx", "vmovaps %ymm1, %ymm0"),
    ("avx512f-off", "-mattr=-avx512f", "vmovaps %zmm1, %zmm0"),
    ("avx512vl-off", "-mattr=-avx512vl", "vmovaps %ymm1, %ymm0"),
    (
        "avx-all-off",
        "-mattr=-avx,-avx512f,-avx512vl",
        "vmovaps %zmm1, %zmm0",
    ),
]


def run(command: list, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, check=True, **kwargs)


def assemble(source: Path, stem: str) -> bytes:
    obj = HERE / (stem + ".o")
    binary = HERE / (stem + ".bin")
    run(["llvm-mc", "-triple=x86_64", "-filetype=obj", str(source), "-o", str(obj)])
    run(
        [
            "llvm-objcopy",
            "-O",
            "binary",
            "--only-section=.text",
            str(obj),
            str(binary),
        ]
    )
    return binary.read_bytes()


def write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def main() -> int:
    measured = assemble(PROBE, "probe")
    if measured != EXPECTED:
        raise SystemExit(
            "probe.asm is %s, expected %s" % (measured.hex(), EXPECTED.hex())
        )
    write(HERE / "bytes.txt", " ".join("%02x" % byte for byte in measured) + "\n")

    shown = run(["llvm-mc", "-triple=x86_64", "-show-encoding", str(PROBE)])
    write(HERE / "show-encoding.txt", shown.stdout)

    disassembled = run(
        ["llvm-mc", "-triple=x86_64", "-disassemble", str(EVEX_WIDTHS)]
    )
    write(HERE / "evex-widths.txt", disassembled.stdout)
    widths = [
        line.split("vmovaps")[1].split(",")[0].strip()
        for line in disassembled.stdout.splitlines()
        if "vmovaps" in line
    ]
    if widths != ["%xmm1", "%ymm1", "%zmm1"]:
        raise SystemExit("evex-widths.s decoded as %r" % (widths,))

    lines = []
    for name, flag, source in MATTR_CASES:
        result = subprocess.run(
            ["llvm-mc", "-triple=x86_64", flag, "-show-encoding"],
            input=".text\n%s\n" % source,
            capture_output=True,
            text=True,
        )
        lines.append(
            "%s\t%s\trc=%d\t%s"
            % (name, flag, result.returncode, source)
        )
        encoded = [
            line.strip()
            for line in result.stdout.splitlines()
            if "encoding:" in line
        ]
        lines.append(
            "\tstdout=%s" % (encoded[0] if encoded else "<none>")
        )
        if result.returncode != 0:
            lines.append("\tstderr=%s" % result.stderr.strip())
    write(HERE / "mattr.txt", "\n".join(lines) + "\n")

    if any(
        line.startswith(("avx-off", "avx512f-off", "avx512vl-off", "avx-all-off"))
        and "rc=0" not in line
        for line in lines
    ):
        raise SystemExit("a -mattr case failed; mattr.txt records the gate")

    print("probe.asm     %d bytes: %s" % (len(measured), measured.hex()))
    print("evex-widths   %s" % ", ".join(widths))
    print("mattr probes  all rc=0 (no per-mnemonic extension gate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
