# EVEX fixed-base SIB probes with no displacement (ADR-0049, X86-P26).
#
# `mod = 00` with `r/m = 100` puts the base in the SIB byte and leaves the
# displacement out entirely.

# xmm width
{evex} vmovaps (%rsp), %xmm0
{evex} vmovaps (%r12), %xmm0
{evex} vmovaps %xmm2, (%rsp)
{evex} vmovaps %xmm2, (%r12)

# ymm width
{evex} vmovaps (%rsp), %ymm0
{evex} vmovaps (%r12), %ymm0
{evex} vmovaps %ymm2, (%rsp)
{evex} vmovaps %ymm2, (%r12)

# zmm width
{evex} vmovaps (%rsp), %zmm0
{evex} vmovaps (%r12), %zmm0
{evex} vmovaps %zmm2, (%rsp)
{evex} vmovaps %zmm2, (%r12)

# The register window: EVEX reaches 16-31 at no length cost.
{evex} vmovaps (%rsp), %xmm20
{evex} vmovaps (%r12), %ymm21
{evex} vmovaps %zmm30, (%rsp)

# The two no-displacement spellings of the same instruction.
{evex} vmovaps 0(%rsp), %xmm0
{evex} vmovaps 0(%r12), %xmm0

# A base that needs no SIB byte keeps `r/m` = base.
{evex} vmovaps (%rax), %xmm0
