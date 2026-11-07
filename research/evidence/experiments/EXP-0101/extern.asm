# EXP-0101 relocation half: the same shape with the link bit clear and set.
#
# `b` uses `R_AARCH64_JUMP26`; `bl` uses `R_AARCH64_CALL26`. The two records
# differ, so the link bit is a property of the form, not a value the fixup or
# the materializer may choose.

.text
  b ext
  bl ext
