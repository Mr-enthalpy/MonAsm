# Value widths the absolute 32-bit address rows do not accept. The plan
# rejects the same pairs as E-OPERAND-001 before any byte is produced.

movl ext, %ax
movq ext, %eax
movw ext, %r9d
