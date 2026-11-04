    movq 16(%rip), %rax
    movq L1(%rip), %rcx
    .space 2
    movq %rdx, L1(%rip)
    .space 9
L1:
    .byte 0xaa, 0xbb, 0xcc, 0xdd
    movq ext(%rip), %rbx
