# EC-24: the fence masks are field values, not a mnemonic choice.
#
# The `imm12` field is `fm`(4) | `pred`(4) | `succ`(4), so `rw, rw` is
# 0x033, `iorw, iorw` is 0x0FF and `r, w` is 0x021 in the same slot.

fence rw, rw
fence iorw, iorw
fence r, w
