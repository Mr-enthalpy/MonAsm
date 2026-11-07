# EXP-0101 field half: `b` with a fixed byte displacement.
#
# `b` is `BL` with bit 31 clear, so `b #0` is `0x14000000` and `b #4` is
# `0x14000001`. llvm-mc's `#n` on a branch is a byte displacement, which is why
# the three values are 0, 4 and -4 rather than 0, 1 and -1.

b #0
b #4
b #-4
