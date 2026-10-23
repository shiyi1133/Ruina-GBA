.section .rodata.screen_animations,"a",%progbits
.balign 4
.global screen_animations_start
screen_animations_start:
.incbin "build/screen_animations.bin"
