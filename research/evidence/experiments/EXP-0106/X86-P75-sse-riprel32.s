movaps L1(%rip), %xmm0
movaps %xmm0, L1(%rip)
vmovaps L1(%rip), %xmm0
vmovaps %xmm0, L1(%rip)
{evex} vmovaps L1(%rip), %xmm0
{evex} vmovaps %xmm0, L1(%rip)
.space 16
L1:
.byte 0xaa, 0xbb, 0xcc, 0xdd
