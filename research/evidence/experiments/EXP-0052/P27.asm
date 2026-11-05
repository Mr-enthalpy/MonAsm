# EVEX SIB index/scale probes (ADR-0050, X86-P27).
#
# `r/m = 100` announces the SIB byte; base, index and scale are operands, and
# `X-bar` (P0 bit 6) is the index's fourth bit.

# The three displacement shapes at xmm width.
{evex} vmovaps (%rsp,%rax,1), %xmm0
{evex} vmovaps 16(%rsp,%rax,1), %xmm2
{evex} vmovaps 8(%rax,%rcx,1), %xmm5

# The scale is the top two SIB bits.
{evex} vmovaps (%rsp,%rax,8), %xmm1
{evex} vmovaps -16(%rsp,%r12,2), %xmm3
{evex} vmovaps 32(%rsp,%rsi,4), %xmm4

# `X-bar` is the index's fourth bit: %rax keeps `f1`, %r12 clears it.
{evex} vmovaps (%rsp,%r12,1), %xmm0
{evex} vmovaps (%r8,%r12,1), %ymm8
{evex} vmovaps (%r12,%r15,8), %xmm31

# `%rbp`/`%r13` cannot be a `mod = 00` SIB base: they keep `disp8*N = 0`.
{evex} vmovaps (%rbp,%rax,1), %xmm7
{evex} vmovaps (%r13,%rax,1), %xmm7
{evex} vmovaps (%rbp,%r12,4), %xmm7

# Store direction, both displacements and the compressed unit.
{evex} vmovaps %xmm0, (%rsp,%rax,1)
{evex} vmovaps %ymm1, 32(%rsp,%rax,1)
{evex} vmovaps 64(%r12,%r12,2), %ymm9
{evex} vmovaps %ymm14, -32(%r12,%r12,8)

# The compressed unit per width: 16 / 32 / 64.
{evex} vmovaps 2032(%rsp,%rax,1), %xmm6
{evex} vmovaps 2048(%rsp,%rax,1), %xmm6
{evex} vmovaps 96(%r8,%r9,4), %zmm17
{evex} vmovaps -64(%rsp,%rax,8), %zmm31
{evex} vmovaps 128(%rsp,%r13,1), %zmm0
{evex} vmovaps 8192(%rax,%rcx,1), %zmm0
{evex} vmovaps -8192(%rax,%rcx,1), %zmm0

# The five-bit vector window.
{evex} vmovaps (%r12,%r12,8), %zmm31

# Zero displacement canonically drops the displacement slot.
{evex} vmovaps 0(%rax,%rcx,1), %xmm0
