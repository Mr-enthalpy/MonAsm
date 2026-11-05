# X86-P13 -- EXP-0038. Assemble with:
#   llvm-mc -triple=x86_64 -filetype=obj P13.asm -o P13.o
#   llvm-objcopy -O binary --only-section=.text P13.o P13.bin
#
# The SSE family's memory operands: load (0F 28) and store (0F 29), in the
# legacy, two-byte-VEX and EVEX families, disp8 and disp32.
#
# {evex} forces the EVEX encoding for the lines llvm-mc would otherwise emit as
# VEX; it does not change the instruction, only which legal encoding is used.
	movaps	8(%rax), %xmm0
	movaps	128(%rax), %xmm1
	movaps	%xmm2, 8(%rax)
	movaps	%xmm3, 128(%rbp)
	vmovaps	8(%rax), %xmm4
	vmovaps	128(%rax), %xmm5
	vmovaps	%xmm6, 8(%rax)
	vmovaps	%xmm7, 128(%rbp)
	{evex}	vmovaps	16(%rax), %xmm0
	{evex}	vmovaps	-16(%rax), %xmm1
	{evex}	vmovaps	2032(%rax), %xmm2
	{evex}	vmovaps	8(%rax), %xmm3
	{evex}	vmovaps	%xmm4, 16(%rax)
	{evex}	vmovaps	%xmm5, 8(%rbp)
