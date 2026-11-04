    movq 0(%rbp), %rax
    movq 8(%rbp), %rcx
    movq -1(%rax), %rdx
    movq 4096(%rbp), %rbx
    movq 8(%rsp), %rsi
    movq 4096(%rsp), %rdi
    movq %rax, 16(%rbp)
    movq %rdx, 4096(%rsp)
