.syntax unified
.cpu arm7tdmi
.section .header,"ax",%progbits
.arm
.global _start
_start:
    b reset
    .space 188
reset:
    mov r0,#0x12
    msr cpsr_c,r0
    ldr sp,=0x03007fa0
    mov r0,#0x1f
    msr cpsr_c,r0
    ldr sp,=0x03007c00
    ldr r0,=__iwram_load
    ldr r1,=__iwram_start
    ldr r2,=__iwram_end
4:
    cmp r1,r2
    ldrlo r3,[r0],#4
    strlo r3,[r1],#4
    blo 4b
    ldr r1,=__iwram_bss_start
    ldr r2,=__iwram_bss_end
    mov r3,#0
5:
    cmp r1,r2
    strlo r3,[r1],#4
    blo 5b
    ldr r0,=__data_load
    ldr r1,=__data_start
    ldr r2,=__data_end
1:
    cmp r1,r2
    ldrlo r3,[r0],#4
    strlo r3,[r1],#4
    blo 1b
    ldr r1,=__bss_start
    ldr r2,=__bss_end
    mov r3,#0
2:
    cmp r1,r2
    strlo r3,[r1],#4
    blo 2b
    ldr r0,=main
    bx r0
3:  b 3b
.arm
.global irq_dispatch
irq_dispatch:
    stmfd sp!,{r4,lr}
    ldr r4,=audio_irq
    mov lr,pc
    bx r4
    ldmfd sp!,{r4,lr}
    bx lr
.section .rodata.save,"a",%progbits
.ascii "SRAM_V113"
.section .rodata.lcf,"a",%progbits
.balign 4
.global original_lcf_start, original_lcf_end
original_lcf_start:
.incbin "build/original_lcf.bin"
original_lcf_end:
.section .rodata.audio,"a",%progbits
.balign 4
.global original_audio_start
original_audio_start:
.incbin "build/audio.bin"
.section .rodata.soundfont,"a",%progbits
.balign 4
.global native_soundfont_start
native_soundfont_start:
.incbin "build/native_music/native_soundfont.bin"
.section .rodata.portraits,"a",%progbits
.balign 4
.global original_portraits_start
original_portraits_start:
.incbin "build/portraits.bin"
.section .rodata.portrait_combinations,"a",%progbits
.align 2
.global portrait_combinations_start
portrait_combinations_start:
.incbin "build/portrait_combinations.bin"
.section .rodata.characters,"a",%progbits
.align 2
.global original_characters_start
original_characters_start:
.incbin "build/characters.bin"
.section .rodata.commands,"a",%progbits
.align 2
.global predecoded_commands_start
predecoded_commands_start:
.incbin "build/commands.bin"
.section .rodata.palette_lookup,"a",%progbits
.balign 4
.global palette_rgb555_start
palette_rgb555_start:
.incbin "build/palette_lookup.bin"

.section .rodata.pages,"a",%progbits
.balign 4
.global predecoded_pages_start
predecoded_pages_start:
.incbin "build/pages.bin"
