# A symbol in an absolute 32-bit content field (`R_X86_64_32S`).
#
# Eight instructions name the external symbol `ext` in an absolute (no base,
# no index, no RIP) 32-bit displacement; the ninth names it in a 32-bit
# immediate. The bytes are zero at the field; the reference travels in the
# relocation.

movl ext, %eax
movl %eax, ext
movl ext, %r8d
movq ext, %rax
movw %r9w, ext
movb %ah, ext
movb ext, %al
vmovaps ext, %zmm1
addq $ext, %rax
