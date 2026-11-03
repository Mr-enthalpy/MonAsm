    .intel_syntax noprefix
    .text
    .globl slice
slice:
    mov rax, rbx
    add rax, 1
    add rax, 300
    mov rax, [rbp - 8]
