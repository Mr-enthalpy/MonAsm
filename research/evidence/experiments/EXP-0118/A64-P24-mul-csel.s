// EXP-0118 / A64-P24: `mul` (the `MADD` alias) and `csel` at both widths.
//
// Row 3 puts 31 in `Rm`: `wzr` is a plain register number on these rows, so
// the field is not excluded. Rows 4-7 are the four conditions that bracket the
// operand: `eq` (0), `ne` (1), `al` (14) and `nv` (15), which the ISA defines.
mul w2, w3, w4
mul x5, x6, x7
mul w0, w1, wzr
csel w8, w9, w10, eq
csel x11, x12, x13, ne
csel x0, x1, x2, al
csel w3, w4, w5, nv
csel xzr, x0, x0, gt
