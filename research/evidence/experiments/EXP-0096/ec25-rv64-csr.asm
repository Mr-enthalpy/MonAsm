# EC-25: the immediate CSR form is a different `funct3`.
#
# `csrrw` is `funct3 = 001` and takes a source register; `csrrwi` is
# `funct3 = 101` and takes a five-bit immediate in the same bits.

csrrw x1, 0x300, x2
csrrwi x1, 0x300, 2
