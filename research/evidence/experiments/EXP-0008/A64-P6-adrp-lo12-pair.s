  .org 0xff8
  adrp x0, blob
  add x0, x0, :lo12:blob
  .org 0x1008
blob:
