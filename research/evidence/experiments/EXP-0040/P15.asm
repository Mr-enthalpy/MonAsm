	movaps %xmm1, %xmm0
	movaps %xmm1, %xmm8
	movaps %xmm9, %xmm0
	movaps %xmm9, %xmm8
	vmovaps %xmm1, %xmm0
	vmovaps %xmm1, %xmm8
	vmovaps %xmm9, %xmm0
	vmovaps %xmm9, %xmm8
	{evex} vmovaps %xmm1, %xmm0
	{evex} vmovaps %xmm1, %xmm8
	{evex} vmovaps %xmm9, %xmm0
	{evex} vmovaps %xmm9, %xmm8
	movaps 8(%rax), %xmm8
	movaps 128(%r8), %xmm9
	movaps %xmm10, 8(%rax)
	movaps %xmm11, 128(%r8)
	vmovaps 8(%rax), %xmm8
	vmovaps 128(%r15), %xmm9
	vmovaps %xmm10, 8(%rax)
	vmovaps %xmm12, 8(%r8)
	{evex} vmovaps 16(%rax), %xmm8
	{evex} vmovaps 16(%r8), %xmm8
	{evex} vmovaps %xmm12, 16(%r8)
