# Deferred and rejected shapes around the EVEX SIB index/scale rows.
#
# `%rbp`/`%r13` at a zero offset are the `disp8*N = 0` row, not `mod = 00`:
# `SIB.base = 101` with `mod = 00` means "no base, disp32".
{evex} vmovaps (%rbp,%rax,1), %xmm0
{evex} vmovaps 0(%rbp,%rax,1), %xmm0

# `SIB.index = 100` with no extension bit is the "no index" encoding, so %rsp
# cannot be an index.
{evex} vmovaps (%rax,%rsp,1), %xmm0

# The scale keyword is 1, 2, 4 or 8; 16 is not a field value.
{evex} vmovaps (%rsp,%rax,16), %xmm0

# The five-bit EVEX register field ends at 31.
{evex} vmovaps (%rsp,%rax,1), %xmm32

# `8` is not a multiple of `N = 16`, so it promotes to `disp32` (11 bytes).
{evex} vmovaps 8(%rsp,%rax,1), %xmm0
