	movaps	8(%r8), %xmm0
	movaps	128(%r15), %xmm1
	movaps	%xmm2, 8(%r8)
	movaps	%xmm3, 128(%r15)
	vmovaps	8(%r8), %xmm4
	vmovaps	128(%r15), %xmm5
	vmovaps	%xmm6, 8(%r8)
	vmovaps	%xmm7, 128(%r15)
	{evex}	vmovaps	16(%r8), %xmm0
	{evex}	vmovaps	16(%r15), %xmm1
	{evex}	vmovaps	2032(%r15), %xmm2
	{evex}	vmovaps	8(%r8), %xmm3
	{evex}	vmovaps	%xmm4, 16(%r9)
	{evex}	vmovaps	%xmm5, 8(%r15)
	movaps	8(%r12), %xmm0
	vmovaps	8(%r12), %xmm0
	{evex}	vmovaps	8(%r12), %xmm0
	movaps	8(%r9), %xmm0
	vmovaps	8(%r9), %xmm0
	{evex}	vmovaps	8(%r9), %xmm0
	movaps	-8(%r10), %xmm7
	vmovaps	-8(%r10), %xmm7
	{evex}	vmovaps	-16(%r10), %xmm7
	movaps	8(%r8), %xmm8
	vmovaps	8(%r8), %xmm8
	{evex}	vmovaps	16(%r8), %xmm8
