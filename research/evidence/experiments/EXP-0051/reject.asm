# Deferred and rejected shapes around the EVEX no-displacement SIB base.
#
# `%rbp`/`%r13` collide with `r/m = 101`, so `mod = 00` cannot name them:
# llvm-mc keeps a displacement byte (content 0).
{evex} vmovaps (%rbp), %xmm0
{evex} vmovaps (%r13), %xmm0

# `mod = 00` with a displacement is a different shape (the `disp8*N` row).
{evex} vmovaps 16(%rsp), %xmm0

# An index (or scale) changes the SIB byte; this slice fixes `SIB = 24`.
{evex} vmovaps (%rsp,%rax,1), %xmm0

# `8` is not a multiple of `N = 16`, so it promotes to `disp32`.
{evex} vmovaps 8(%rsp), %xmm0

# The five-bit EVEX register field ends at 31.
{evex} vmovaps (%rsp), %xmm32
