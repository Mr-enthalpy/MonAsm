# RV-P10 field coverage: the three `jalr` immediates that matter.
#
# `jalr rd, imm(rs1)`. The immediate is a displacement from `rs1`, not from
# `pc`; `.option norvc` is explicit because `jalr ra, 0(ra)` would otherwise
# become the two-byte `c.jalr` (EXP-0096), a different form.

.option norvc
jalr a0, 0(a1)
jalr x0, 2047(a1)
jalr x0, -2048(a1)
