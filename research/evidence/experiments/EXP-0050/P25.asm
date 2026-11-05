# EVEX fixed-base SIB probes (ADR-0048, X86-P25).

# xmm width: N = 16
{evex} vmovaps 16(%rsp), %xmm0
{evex} vmovaps 16(%r12), %xmm0
{evex} vmovaps 128(%rsp), %xmm1
{evex} vmovaps 128(%r12), %xmm1
{evex} vmovaps %xmm2, 16(%rsp)
{evex} vmovaps %xmm2, 16(%r12)
{evex} vmovaps %xmm3, 128(%rsp)
{evex} vmovaps %xmm3, 128(%r12)
{evex} vmovaps 2048(%rsp), %xmm4
{evex} vmovaps 2048(%r12), %xmm4
{evex} vmovaps -16(%rsp), %xmm5
{evex} vmovaps -16(%r12), %xmm5

# ymm width: N = 32
{evex} vmovaps 32(%rsp), %ymm0
{evex} vmovaps 32(%r12), %ymm0
{evex} vmovaps 4096(%rsp), %ymm1
{evex} vmovaps 4096(%r12), %ymm1
{evex} vmovaps %ymm2, 64(%rsp)
{evex} vmovaps %ymm2, 64(%r12)

# zmm width: N = 64
{evex} vmovaps 64(%rsp), %zmm0
{evex} vmovaps 64(%r12), %zmm0
{evex} vmovaps 8192(%rsp), %zmm1
{evex} vmovaps 8192(%r12), %zmm1
{evex} vmovaps %zmm2, 128(%rsp)
{evex} vmovaps %zmm2, 128(%r12)

# Register windows: EVEX reaches 16-31 at no length cost.
{evex} vmovaps 16(%rsp), %xmm20
{evex} vmovaps 64(%r12), %zmm30
{evex} vmovaps %ymm21, 32(%rsp)
