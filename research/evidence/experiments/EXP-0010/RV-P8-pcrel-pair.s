.L0:
  auipc a0, %pcrel_hi(blob)
  addi a0, a0, %pcrel_lo(.L0)
  sd a1, %pcrel_lo(.L0)(a0)
