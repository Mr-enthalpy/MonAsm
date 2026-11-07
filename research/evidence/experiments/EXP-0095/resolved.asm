# The same rows with a defined symbol and a bound section, resolved in place.
#
# `.text` is placed at 0x1000 by the linker script below, so `L1` (offset 30)
# is 0x101e. Each displacement is the address the linker writes, not content.

movq L1, %rax
movl L1+4, %eax
movl %ecx, L1
movw %dx, L1+2
L1:
movb L1, %al
