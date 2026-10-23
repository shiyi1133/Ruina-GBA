"""Build the freestanding ARM7 GBA development ROM; no commercial ROM is patched."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from project_env import arm_prefix
ROOT=Path(__file__).resolve().parents[1]
PREFIX=Path(arm_prefix())
def run(args):subprocess.run([str(a)for a in args],cwd=ROOT,check=True)
def asset_python():
 # Full source-art conversion needs Pillow/NumPy. Cached incremental builds
 # use only Python's standard library and do not invoke this interpreter.
 return os.environ.get('RUINA_ASSET_PYTHON',sys.executable)
def main():
 out=ROOT/'build';out.mkdir(exist_ok=True)
 if not (out/'original_lcf.bin').exists():run([sys.executable,ROOT/'tools/preserve_source.py'])
 
 if '--incremental' not in sys.argv:run([asset_python(),ROOT/'tools/assets.py'])
 if not (out/'audio.bin').exists():run([asset_python(),ROOT/'tools/audio_assets.py'])
 if json.loads((out/'audio_manifest.json').read_text()).get('gameplay'):run([sys.executable,ROOT/'tools/scaled_music_assets.py'])
 if not (out/'portraits.bin').exists():run([sys.executable,ROOT/'tools/portrait_assets.py'])
 if not (out/'portrait_combinations.bin').exists():run([asset_python(),ROOT/'tools/portrait_combinations.py'])
 if not (out/'characters.bin').exists():run([asset_python(),ROOT/'tools/character_assets.py'])
 run([sys.executable,ROOT/'tools/battle_animation_assets.py'])
 run([sys.executable,ROOT/'tools/compact_scene_lookups.py'])
 run([sys.executable,ROOT/'tools/bake_screen_animations.py'])
 run([sys.executable,ROOT/'tools/command_assets.py'])
 run([sys.executable,ROOT/'tools/page_assets.py'])
 run([sys.executable,ROOT/'tools/borrowed_command_assets.py'])
 run([sys.executable,ROOT/'tools/palette_lookup.py'])
 run([sys.executable,ROOT/'tools/source_menu_assets.py'])
 run([sys.executable,ROOT/'tools/midi_clock_assets.py'])
 run([sys.executable,ROOT/'tools/music_room_assets.py'])
 run([sys.executable,ROOT/'tools/tile_tables.py'])
 objects=[]
 sources=[]
 for directory in ['source','runtime/rm2k','platform/gba']:sources+=sorted((ROOT/directory).glob('*.c'))
 audio_metadata=json.loads((out/'audio_manifest.json').read_text());light_music=bool(audio_metadata.get('gameplay'))
 # Bind the receipt to compiler inputs, excluding generated fixture-only headers.
 input_paths=[]
 for directory in ('source','runtime/rm2k','platform/gba'):input_paths += sorted((ROOT/directory).glob('*.c'))+sorted((ROOT/directory).glob('*.h'))+sorted((ROOT/directory).glob('*.inc'))
 input_paths += [ROOT/'platform/gba/start.s',ROOT/'platform/gba/gba.ld']
 input_paths += [out/name for name in ('assets.c','assets.h','borrowed_commands.c','source_menu_labels.c','midi_clock.c','music_room_names.c','autotile_tables.h','original_lcf.bin','audio.bin','portraits.bin','portrait_combinations.bin','characters.bin','battle_animation_assets.h','battle_animations.bin','portraits_packed.bin','commands.bin','pages.bin','palette_lookup.bin','native_music/native_soundfont.bin','high_color_blobs.s','high_color_blobs.bin')if(out/name).exists()]
 input_paths += [out/p for p in ('scene_lookups_packed.bin','screen_animation_assets.h','screen_animation_blobs.s','screen_animations.bin')if(out/p).exists()]
 inputs_before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in input_paths}
 extra=[out/'high_color_blobs.s']if(out/'high_color_blobs.s').exists()else[]
 if(out/'screen_animation_blobs.s').exists():extra.append(out/'screen_animation_blobs.s')
 for src in sources+[out/'assets.c',out/'borrowed_commands.c',out/'source_menu_labels.c',out/'midi_clock.c',out/'music_room_names.c',ROOT/'platform/gba/start.s']+extra:
  obj=out/(src.stem+'.o');objects.append(obj)
  flags=['-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-Os','-ffreestanding','-fno-builtin','-fdata-sections','-ffunction-sections','-fstack-usage','-g']
  flags+=['-Isource','-Iruntime/rm2k','-Iplatform/gba','-Ibuild']
  if light_music:flags+=['-DRUINA_LIGHT_MUSIC','-DRUINA_LIGHT_VOICES=128']
  flags+=['-DRUINA_PREDECODE_COMMANDS','-DRUINA_PREDECODE_PAGES','-DRUINA_BORROW_COMMANDS']
  if audio_metadata.get('direct_pcm_wav'):flags+=['-DRUINA_PCM_WAV']
  if src.name in ('audio.c','native_midi.c','light_midi.c'):flags+=['-marm','-O3','-mlong-calls']
  if src.name in ('lcf.c','image.c'):flags+=['-marm','-O3','-mlong-calls']
  if src.suffix=='.c':flags+=['-std=c99','-Wall','-Wextra','-Wno-misleading-indentation','-finput-charset=UTF-8','-fexec-charset=GBK']
  run([str(PREFIX)+'gcc',*flags,'-c',src,'-o',obj])
 elf=out/'ruina_opening_dev.elf'
 run([str(PREFIX)+'gcc','-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-nostdlib','-Wl,-T,platform/gba/gba.ld','-Wl,-Map,build/ruina_opening_dev.map',*objects,'-lgcc','-o',elf])
 rom=out/'废都物语_GBA_开篇开发验证版.gba';run([str(PREFIX)+'objcopy','-O','binary',elf,rom])
 data=bytearray(rom.read_bytes())
 logo=bytes.fromhex('24ffae51699aa2213d84820a84e409ad11248b98c0817f21a352be199309ce2010464a4af82731ec58c7e83382e3cebf85f4df94ce4b09c194568ac01372a7fc9f844d73a3ca9a615897a327fc039876231dc7610304ae56bf38840040a70efdff52fe036f9530f197fbc08560d68025a963be03014e38e2f9a234ffbb3e0344780090cb88113a9465c07c6387f03cafd625e48b380aac7221d4f807')
 assert len(logo)==156;data[4:160]=logo;data[160:172]=b'RUINA GBA   ';data[172:176]=b'RUIN';data[176:178]=b'00';data[178]=0x96;data[179:188]=bytes(9);data[188]=0;data[189]=(-sum(data[160:189])-0x19)&255;data[190:192]=b'\0\0'
 data[172:176]=b'RUBA';data[189]=(-sum(data[160:189])-0x19)&255
 data+=b'\xff'*((-len(data))%4);assert len(data)<=32*1024*1024,'GBA ROM exceeds 32 MiB';rom.write_bytes(data)
 run([str(PREFIX)+'size',elf])
 report={'artifact':rom.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'kind':'native GBA RM2000 compatibility framework with Ruina chapter adapter','build_status':'compiled','runtime_validation':'not run by this build command; see evidence/animation_smooth_20261023/validation.json for the matching ROM hash','full_game_port':False,'complete_EasyRPG_port':False,'upstream_lock_sha256':hashlib.sha256((ROOT/'third_party/sources.lock.json').read_bytes()).hexdigest()}
 assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in inputs_before.items()),'Compiler inputs changed during build'
 report['compiler_inputs_sha256']=inputs_before;report['compiler_inputs_unchanged_during_build']=True;report['light_music_voice_capacity']=128 if light_music else None
 report['version']='0.7.4';report['renderer']='retained native BG0 maps + independent 4bpp BG1 text windows; RGB555 bitmap illustrations, portraits and battle scenes'
 (out/'build_receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
