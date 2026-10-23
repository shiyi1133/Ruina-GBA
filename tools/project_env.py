"""Local paths are overrideable; original game material stays unchanged."""
import os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=Path(os.environ.get('RUINA_SOURCE_ARCHIVE','/mnt/e/下载/废都物语251102修复优化版.zip'))
FONT=Path(os.environ.get('RUINA_FONT','/mnt/c/Windows/Fonts/simsun.ttc'))
def arm_prefix():
 if os.environ.get('ARM_TOOLCHAIN_PREFIX'):return os.environ['ARM_TOOLCHAIN_PREFIX']
 gcc=shutil.which('arm-none-eabi-gcc')
 if gcc:return (gcc[:-4]if gcc.lower().endswith('.exe')else gcc)[:-3]
 return '/home/app/gba-runtime/test-manager/mode_entry_npc/tree-blend-3a7dcbc-20260923/rebuild-v001/selective/selective-check/parent/toolchain/usr/bin/arm-none-eabi-'
