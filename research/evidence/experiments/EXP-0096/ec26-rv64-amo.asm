# EC-26: `aq` and `rl` are two fixed bits, one per suffix.
#
# The A-extension word is 0x0021A0AF for the bare `amoadd.w`; `.aq` sets
# bit 26 (0x0421A0AF), `.rl` sets bit 25 (0x0221A0AF) and `.aqrl` sets both.

amoadd.w x1, x2, (x3)
amoadd.w.aq x1, x2, (x3)
amoadd.w.rl x1, x2, (x3)
amoadd.w.aqrl x1, x2, (x3)
