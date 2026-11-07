# RV-P10 arithmetic half: the same pair linked, so the two fields are measured
# rather than derived. `.text` lands at 0x1000 and `L1` at 0x1900, so the high
# half is 1 (a zero high half would not tell `pcrel_hi20` apart from a plan that
# wrote the wrong value there) and the low half is 0x900 -- bit 11 set, so the
# instruction sign-extends it to -0x700 at run time. The assembler is given the
# negative spelling; the plan writes the same bits through a mask.

.text
.option norvc
.L0:
  auipc ra, %pcrel_hi(L1)
  jalr ra, %pcrel_lo(.L0)(ra)
  .space 0x8f8
L1:
  .word 0
