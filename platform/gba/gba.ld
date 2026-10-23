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
  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.note*) }
}
