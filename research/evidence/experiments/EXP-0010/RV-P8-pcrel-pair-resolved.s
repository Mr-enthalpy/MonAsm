  .org 0x4
.L0:
  auipc a0, %pcrel_hi(blob)
  addi a0, a0, %pcrel_lo(.L0)
  .org 0x1000
blob:
