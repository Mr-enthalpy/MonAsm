# EC-23: one "jump", three instructions and three lengths.
#
# On RV64 there is no `c.jal`, so `jal ra` stays four bytes, but `jal x0`
# becomes the two-byte `c.j` when the C extension is enabled, and
# `jalr ra, 0(ra)` becomes the two-byte `c.jalr`. The compressed form is
# therefore a form the plan names, never a shortening the materializer picks.

.option rvc
1: jal ra, 1b
1: jal x0, 1b
1: c.j 1b
1: jalr ra, 0(ra)
.option norvc
1: jal x0, 1b
1: jalr ra, 0(ra)
