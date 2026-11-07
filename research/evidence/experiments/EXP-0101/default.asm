# EXP-0101 default half: the assembler's `ret` is `ret x30`.
#
# The encoding is `0xd65f03c0` and `ret x30` is the same word. v0 has no
# `aarch64:ret` form, so a plan that leans on the default is `E-FORM-001`
# (`N01y`) instead of silently returning through x30.

ret
