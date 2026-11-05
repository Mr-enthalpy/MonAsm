# EVEX probes: force the EVEX encoding with the {evex} pseudo-prefix.
	{evex} vmovaps	16(%rax), %xmm0
	{evex} vmovaps	32(%rax), %xmm0
	{evex} vmovaps	8(%rax), %xmm0
	{evex} vmovaps	128(%rax), %xmm0
	{evex} vmovaps	256(%rax), %xmm0
	{evex} vmovaps	16(%r8), %xmm0
	{evex} vmovaps	16(%r12), %xmm0
	{evex} vmovaps	16(%r13), %xmm0
	{evex} vmovaps	8(%rax), %xmm8
	{evex} vmovaps	%xmm0, 16(%rax)
	{evex} vmovaps	16(%rbp), %xmm0
