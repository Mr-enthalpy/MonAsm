.text
jmp L1
.space 200, 0x00
movq %rbx, %rax
L1:
addq $1, %rax
jmp ext
