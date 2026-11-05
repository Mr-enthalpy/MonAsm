# `SIB.index = 100` with no extension bit is the "no index" encoding, so %rsp
# cannot be an index here either.
{evex} vmovaps (,%rsp,1), %xmm0

# The scale keyword is 1, 2, 4 or 8; 16 is not a field value.
{evex} vmovaps (,%rax,16), %xmm0

# The five-bit EVEX register field ends at 31.
{evex} vmovaps (,%rax,1), %xmm32

# disp32 is signed; 0x80000000 is one past the field.
{evex} vmovaps 0x80000000, %xmm0

# With a base the same address is the `disp8*N` row, not this shape.
{evex} vmovaps 0(%rbp,%rax,1), %xmm0
