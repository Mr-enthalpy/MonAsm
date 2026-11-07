# EC-10: a prefix byte is a distinct encoding, not an operand modifier.
#
# `lock` and `rep` change the semantics and add one byte; a segment override
# adds a byte and changes the address space. All three are measured here,
# although v0 carries no row for any of them.

addl (%rax), %ebx
lock addl (%rax), %ebx
movsb %ds:(%rsi), %es:(%rdi)
rep movsb
movl %fs:0, %eax
