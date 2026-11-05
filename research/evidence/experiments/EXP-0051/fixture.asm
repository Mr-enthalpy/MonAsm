# EVEX no-displacement fixed-base SIB fixture (ADR-0049, X86-P26).
#
# One instruction per 0.22.0 row: three widths, load/store, `%rsp`/`%r12`.

# xmm width
{evex} vmovaps (%rsp), %xmm0
{evex} vmovaps (%r12), %xmm1
{evex} vmovaps %xmm2, (%rsp)
{evex} vmovaps %xmm3, (%r12)

# ymm width
{evex} vmovaps (%rsp), %ymm8
{evex} vmovaps (%r12), %ymm9
{evex} vmovaps %ymm10, (%rsp)
{evex} vmovaps %ymm11, (%r12)

# zmm width
{evex} vmovaps (%rsp), %zmm16
{evex} vmovaps (%r12), %zmm17
{evex} vmovaps %zmm18, (%rsp)
{evex} vmovaps %zmm19, (%r12)
