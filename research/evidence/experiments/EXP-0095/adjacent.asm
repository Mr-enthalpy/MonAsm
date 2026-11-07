# Neighbours of the absolute 32-bit address field: the spellings that keep
# their displacement as content, use a different field, or need a different
# width. None of these is this slice.

movl ext, %eax          # absolute 32-bit address: R_X86_64_32S (this slice)
movl ext(%rip), %eax    # RIP-relative: R_X86_64_PC32, pcrel_end
movabs ext, %rax        # moffs: R_X86_64_64, an eight-byte offset
movl $ext, %eax         # immediate field: R_X86_64_32 (no mov imm form yet)
addq $ext, %rax         # immediate field on an existing row: R_X86_64_32S
