# EXP-0101 indirect half: the three register branches.
#
# `br`/`blr`/`ret` share a template and differ only in `op` at bits 22-21
# (`00`, `01`, `10`). `Rn` is bits 9-5. `ret` with no operand is `ret x30` in
# the assembler; the plan must name the register, so that default is absent in
# the definition (`N01y`).

br x1
br x0
blr x2
ret x30
ret x0
ret x19
