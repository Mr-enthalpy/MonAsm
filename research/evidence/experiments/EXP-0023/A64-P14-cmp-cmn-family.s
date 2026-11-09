  cmp x1, x2
  cmp x3, x4, lsl #5
  cmp x5, x6, lsr #7
  cmp x7, x8, asr #9
  cmp x9, #5
  cmp x10, #291, lsl #12
  cmp w11, w12
  cmp w13, w14, lsl #15
  cmp w15, w16, lsr #17
  cmp w17, w18, asr #19
  cmp w19, #5
  cmp w20, #291, lsl #12
  cmp x21, w22, uxtb
  cmp x23, w24, uxth #1
  cmp x25, w26, uxtw #2
  cmp x27, x28, uxtx #3
  cmp x29, w30, sxtb #4
  cmp x0, w1, sxth
  cmp x2, w3, sxtw #1
  cmp x4, x5, sxtx #2
  cmn x6, x7
  cmn x8, x9, lsl #5
  cmn x10, x11, lsr #7
  cmn x12, x13, asr #9
  cmn x14, #5
  cmn x15, #291, lsl #12
  cmn w16, w17
  cmn w18, w19, lsl #15
  cmn w20, w21, lsr #17
  cmn w22, w23, asr #19
  cmn w24, #5
  cmn w25, #291, lsl #12
  cmn x26, w27, uxtb
  cmn x28, w29, uxth #1
  cmn x30, w0, uxtw #2
  cmn x1, x2, uxtx #3
  cmn x3, w4, sxtb #4
  cmn x5, w6, sxth
  cmn x6, w7, sxtw #1
  cmn x8, x9, sxtx #2
  cmp sp, #5
  cmp wsp, #5
  cmp sp, x2
  cmn sp, #5
  cmn sp, x2
  cmp x1, xzr
  cmp w1, wzr
