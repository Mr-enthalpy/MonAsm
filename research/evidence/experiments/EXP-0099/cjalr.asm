# The absent sibling: with C enabled the same source line is the two-byte
# `c.jalr`, a different instruction with a different `form_id`. The materializer
# must never pick it, so a plan names `riscv:c.jalr/rs1-imm12` and gets
# `E-FORM-001`.

.text
.option rvc
jalr ra, 0(ra)
