# RV-P10 record half: the `auipc` + `jalr` call pair against an external symbol.
#
# `%pcrel_lo(.L0)` names the label of the `auipc`, so the low half is measured
# from the high half's site, not from the `jalr`'s own address.

.text
.option norvc
.L0:
  auipc ra, %pcrel_hi(blob)
  jalr ra, %pcrel_lo(.L0)(ra)
