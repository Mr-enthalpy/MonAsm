	{evex} vmovaps (%rax), %ymm0
	{evex} vmovaps %ymm0, (%rax)
	{evex} vmovaps (%r8), %ymm31
	{evex} vmovaps %ymm31, (%r8)
	{evex} vmovaps 32(%rax), %ymm0
	{evex} vmovaps -32(%rax), %ymm0
	{evex} vmovaps 4064(%rax), %ymm0
	{evex} vmovaps -4096(%rax), %ymm0
	{evex} vmovaps 28(%rax), %ymm0
	{evex} vmovaps 4096(%rax), %ymm0
	{evex} vmovaps 32(%r8), %ymm31
	{evex} vmovaps %ymm31, -32(%r8)
	{evex} vmovaps %ymm31, 28(%r8)
	vmovaps (%rax), %zmm0
	vmovaps %zmm0, (%rax)
	vmovaps (%r8), %zmm31
	vmovaps %zmm31, (%r8)
	vmovaps 64(%rax), %zmm0
	vmovaps -64(%rax), %zmm0
	vmovaps 8128(%rax), %zmm0
	vmovaps -8192(%rax), %zmm0
	vmovaps 60(%rax), %zmm0
	vmovaps 8192(%rax), %zmm0
	vmovaps 64(%r8), %zmm31
	vmovaps %zmm31, -64(%r8)
	vmovaps %zmm31, 60(%r8)
