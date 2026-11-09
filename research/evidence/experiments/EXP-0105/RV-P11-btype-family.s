bne a0, a1, L1
blt a0, a1, L2
L1:
bge a0, a1, L3
L2:
bltu a0, a1, L1
L3:
bgeu a0, a1, L2
