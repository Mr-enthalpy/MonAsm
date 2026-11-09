movk x0, #0x1234
movk x1, #0x00ff, lsl #16
movk x2, #0xbeef, lsl #32
movk x3, #0x0001, lsl #48
movn x4, #0x1234
movn x5, #0x00ff, lsl #16
movn x6, #0xbeef, lsl #32
movn x7, #0x0001, lsl #48
movk x31, #0
movn x31, #0xffff
movk x8, #0xffff, lsl #48
movn x8, #0, lsl #48
