movaps 8(%rsp), %xmm8
movaps 8(%r12), %xmm9
movaps 128(%rsp), %xmm14
movaps 128(%r12), %xmm15
movaps %xmm10, 8(%rsp)
movaps %xmm11, 8(%r12)
movaps %xmm12, 128(%rsp)
movaps %xmm13, 128(%r12)

