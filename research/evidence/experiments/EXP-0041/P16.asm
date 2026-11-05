	movaps (%rcx), %xmm2
	movaps %xmm2, (%rcx)
	movaps (%rcx), %xmm9
	movaps %xmm9, (%rcx)
	movaps (%r9), %xmm2
	movaps %xmm2, (%r9)
	movaps (%r9), %xmm10
	movaps %xmm10, (%r9)
	vmovaps (%rdx), %xmm8
	vmovaps %xmm9, (%rbx)
	vmovaps (%r11), %xmm10
	vmovaps %xmm11, (%r10)
	{evex} vmovaps (%rax), %xmm0
	{evex} vmovaps (%r8), %xmm0
	{evex} vmovaps (%rax), %xmm8
	{evex} vmovaps (%r8), %xmm8
