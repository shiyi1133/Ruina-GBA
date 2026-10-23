/* Host-only immutable bank identities; no emulated RAM is written. */
__asm__(".section .rodata\n.balign 4\n.global original_lcf_start\noriginal_lcf_start:\n .incbin \"build/original_lcf.bin\"\n.global original_lcf_end\noriginal_lcf_end:\n.balign 4\n.global predecoded_commands_start\npredecoded_commands_start:\n.incbin \"build/commands.bin\"\n.previous\n");
