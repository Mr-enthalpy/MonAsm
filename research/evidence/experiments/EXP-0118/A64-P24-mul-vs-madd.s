// EXP-0118: the two contrasts behind EC-44 and the `csel` row.
//
// `mul` is `madd` with `Ra` (14-10) fixed to 31; the first pair differs only
// in that field. `csel` and `csinc` share every field except `o2` at bit 10,
// which the CSEL node fixes to 0 and the CSINC node to 1.
mul x0, x1, x2
madd x0, x1, x2, x3
csel x0, x1, x2, eq
csinc x0, x1, x2, eq
