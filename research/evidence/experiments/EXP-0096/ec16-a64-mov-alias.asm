# EC-16: one `mov` mnemonic, three encoding nodes.
#
# `mov x0, #1` is MOVZ, `mov x0, #-1` is MOVN, `mov x0, x1` is ORR
# (shifted register) and `mov x0, #65536` is MOVZ with `hw = 01`.

mov x0, #1
mov x0, #-1
mov x0, x1
mov x0, #65536
mov w0, #1
