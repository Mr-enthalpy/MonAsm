# EXP-0101 arithmetic half: three `b` instructions resolved against local
# labels, so the 26-bit field is measured rather than derived.
#
# `back` is at 0, `here` at 4 and `ahead` at 8. The three sites are at 0, 4 and
# 8, so the byte displacements are +8, 0 and -8 and the field values are 2, 0
# and -2.

.text
back:
  b ahead
here:
  b here
ahead:
  b back
