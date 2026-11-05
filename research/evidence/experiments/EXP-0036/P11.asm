# X86-P11 — `EXP-0036`. Assemble with:
#   llvm-mc -triple=x86_64 -filetype=obj P11.asm -o P11.o
#   llvm-objcopy -O binary --only-section=.text P11.o P11.bin
#
# Bases r8-r11, r13-r15 use the general rows (REX.B only); rsp and r12 have the
# same low three bits, so each goes through its own fixed-base row where REX.B
# is the only difference (0x48 vs 0x49).
	movq	8(%r8), %r9
	movq	8(%r11), %rax
	movq	8(%r13), %r15
	movq	8(%r14), %rcx
	movq	8(%r15), %rdx
	movq	-1(%r11), %rdx
	movq	127(%r15), %rax
	movq	128(%r8), %r9
	movq	128(%r13), %r15
	movq	8(%rsp), %r9
	movq	8(%r12), %r9
	movq	128(%rsp), %r15
	movq	128(%r12), %r15
	movq	%r9, 8(%rsp)
	movq	%r9, 8(%r12)
	movq	%r15, 128(%r13)
	movq	%r15, 128(%r12)
