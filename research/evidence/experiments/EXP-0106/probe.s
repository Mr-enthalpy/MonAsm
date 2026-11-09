movaps 16(%rip), %xmm0
movaps %xmm0, 16(%rip)
vmovaps 16(%rip), %xmm0
vmovaps %xmm0, 16(%rip)
{evex} vmovaps 16(%rip), %xmm0
{evex} vmovaps %xmm0, 16(%rip)

