ENTRY(_start)
MEMORY {
  ROM (rx) : ORIGIN = 0x08000000, LENGTH = 32M
  RAM (rwx) : ORIGIN = 0x02000000, LENGTH = 256K
  IWRAM (rwx) : ORIGIN = 0x03000000, LENGTH = 28K
}
SECTIONS {
  .text : { KEEP(*(.header)) *(.text*) *(.rodata*) . = ALIGN(4); } > ROM
  .data : { __data_start = .; *(.data*) . = ALIGN(4); __data_end = .; } > RAM AT > ROM
  __data_load = LOADADDR(.data);
  .bss (NOLOAD) : { __bss_start = .; *(.bss*) *(COMMON) . = ALIGN(4); __bss_end = .; } > RAM
  .iwram : { __iwram_start = .; *(.iwram) . = ALIGN(4); __iwram_end = .; } > IWRAM AT > ROM
  __iwram_load = LOADADDR(.iwram);
  .iwram_bss (NOLOAD) : { __iwram_bss_start = .; *(.iwram_bss) . = ALIGN(4); __iwram_bss_end = .; } > IWRAM
  OVERLAY ALIGN(4) : NOCROSSREFS AT(LOADADDR(.iwram) + SIZEOF(.iwram)) {
    .animation_workspace { *(.animation_workspace) . = ALIGN(4); }
    .animation_prepare { *(.animation_prepare*) . = ALIGN(4); }
  } > IWRAM
  ASSERT(SIZEOF(.animation_prepare) <= SIZEOF(.animation_workspace), "Animation preparation exceeds shared drawing workspace")
  OVERLAY ALIGN(4) : NOCROSSREFS AT(LOADADDR(.animation_prepare) + SIZEOF(.animation_prepare)) {
    .animation_encoder { *(.animation_encoder*) . = ALIGN(4); }
    .animation_restore { *(.animation_restore*) . = ALIGN(4); }
  } > IWRAM
  __animation_codec_start = ADDR(.animation_encoder);
  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.note*) }
}
