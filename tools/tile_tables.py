"""Copy pinned upstream autotile quadrant tables, retaining provenance."""
from project_env import ROOT
def main():
 src=(ROOT/'third_party/Player/src/tilemap_layer.cpp').read_text();parts=['/* Autotile tables from pinned EasyRPG Player tilemap_layer.cpp.',' * Copyright EasyRPG authors; GPL-3.0-or-later; see third_party/Player/COPYING. */']
 for old,new,kind in [('BlockA_Subtiles_IDS','block_a','signed char'),('BlockD_Subtiles_IDS','block_d','unsigned char')]:
  at=src.index('static constexpr',src.index('// Blocks subtiles IDs'))
  at=src.rfind('static constexpr',0,src.index(old));end=src.index('};',src.index(old))+2
  text=src[at:end].replace('static constexpr int8_t '+old,'static const '+kind+' '+new).replace('static constexpr uint8_t '+old,'static const '+kind+' '+new);parts.append(text)
 (ROOT/'build/autotile_tables.h').write_text('\n'.join(parts)+'\n')
if __name__=='__main__':main()
