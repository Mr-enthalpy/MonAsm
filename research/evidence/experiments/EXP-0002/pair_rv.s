    .text
.L0:
    auipc a0, %pcrel_hi(ext)
    addi  a0, a0, %pcrel_lo(.L0)
