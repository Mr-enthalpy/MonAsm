    .text
    lui a0, %hi(L1)
    addi a0, a0, %lo(L1)
    .space 0x22c
L1:
    .word 0
