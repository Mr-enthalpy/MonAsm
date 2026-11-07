# EC-18: three conditional-transfer forms, three operand sets.
#
# `b.eq` carries a condition and `imm19`; `cbz`/`cbnz` carry one register and
# `imm19` but no condition; `tbz`/`tbnz` carry a register, a bit index and
# `imm14`. Only the `b.cond` family ships in v0.

1: b.eq 1b
1: cbz x0, 1b
1: cbnz w0, 1b
1: tbz w0, #0, 1b
1: tbnz x0, #63, 1b
