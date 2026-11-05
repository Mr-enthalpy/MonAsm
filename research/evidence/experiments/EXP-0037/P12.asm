# X86-P12 -- EXP-0037. Assemble with:
#   llvm-mc -triple=x86_64 -filetype=obj P12.asm -o P12.o
#   llvm-objcopy -O binary --only-section=.text P12.o P12.bin
#
# A SIB byte on every instruction: base + index*scale + disp.  mod=01 (disp8)
# except the two disp32 rows.  The scale field is the operand value 0..3, so
# (/rcx,1) is 0, (/rcx,2) is 1, (/rcx,4) is 2 and (/rcx,8) is 3.
	movq	8(%rax,%rcx,1), %rdx
	movq	8(%rax,%rcx,2), %rdx
	movq	8(%rax,%rcx,4), %rdx
	movq	8(%rax,%rcx,8), %rdx
	movq	8(%r8,%r9,2), %r10
	movq	8(%rax,%r12,4), %rdx
	movq	8(%r12,%r13,8), %r15
	movq	128(%r8,%r14,2), %r11
	movq	%rdx, 8(%rax,%rcx,4)
	movq	%r15, 128(%r12,%r13,8)
	movq	8(%rsp,%rcx,1), %rdx
	movq	8(%rax,%rbp,1), %rdx
	movq	8(%r13,%r12,8), %rdx
