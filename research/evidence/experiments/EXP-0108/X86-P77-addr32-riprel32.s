addr32 movl L1(%rip), %eax
addr32 movl %eax, L1(%rip)
addr32 movq L1(%rip), %rax
addr32 movq %rax, L1(%rip)
addr32 movw L1(%rip), %ax
addr32 movw %ax, L1(%rip)
.space 16
L1:
.byte 0xaa, 0xbb, 0xcc, 0xdd
