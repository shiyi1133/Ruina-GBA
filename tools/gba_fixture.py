"""Link a separate controlled cartridge without changing the playable ROM."""
import hashlib,json,subprocess
from drive_opening import ROOT,PREFIX

def fixture(source,stem,overrides=None):
 production=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=hashlib.sha256(production.read_bytes()).hexdigest()
 out=ROOT/'build/fixtures'/stem;out.mkdir(parents=True,exist_ok=True)
 flags=['-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-Os','-ffreestanding','-fno-builtin','-fdata-sections','-ffunction-sections','-g','-Isource','-Iruntime/rm2k','-Iplatform/gba','-Ibuild','-std=c99','-finput-charset=UTF-8','-fexec-charset=GBK']
 if json.loads((ROOT/'build/audio_manifest.json').read_text()).get('gameplay'):flags+=['-DRUINA_LIGHT_MUSIC','-DRUINA_LIGHT_VOICES=128']
 flags+=['-DRUINA_PREDECODE_COMMANDS','-DRUINA_PREDECODE_PAGES','-DRUINA_BORROW_COMMANDS']
 if json.loads((ROOT/'build/audio_manifest.json').read_text()).get('direct_pcm_wav'):flags+=['-DRUINA_PCM_WAV']
 obj=out/'main.o';subprocess.run([PREFIX+'gcc',*flags,'-c',str(ROOT/source),'-o',str(obj)],cwd=ROOT,check=True)
 objects=[]
 for directory in ['source','runtime/rm2k','platform/gba']:objects += [ROOT/'build'/(p.stem+'.o')for p in sorted((ROOT/directory).glob('*.c'))if p.name!='game.c']
 for name,path in (overrides or {}).items():
  replacement=out/(name+'.o')
  subprocess.run([PREFIX+'gcc',*flags,*(['-marm','-O3','-mlong-calls']if name in('audio','lcf','light_midi','native_midi')else[]),'-c',str(ROOT/path),'-o',str(replacement)],cwd=ROOT,check=True)
  objects=[replacement if p.name==name+'.o'else p for p in objects]
 objects += [ROOT/'build'/n for n in ['assets.o','borrowed_commands.o','source_menu_labels.o','midi_clock.o','music_room_names.o','start.o']]+[obj]
 if(ROOT/'build/high_color_blobs.s').exists():objects.append(ROOT/'build/high_color_blobs.o')
 elf=out/(stem+'.elf');rom=out/(stem+'.gba')
 subprocess.run([PREFIX+'gcc','-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-nostdlib','-Wl,-T,platform/gba/gba.ld',*map(str,objects),'-lgcc','-o',str(elf)],cwd=ROOT,check=True)
 subprocess.run([PREFIX+'objcopy','-O','binary',str(elf),str(rom)],check=True)
 b=bytearray(rom.read_bytes());b[4:192]=production.read_bytes()[4:192];rom.write_bytes(b)
 assert hashlib.sha256(production.read_bytes()).hexdigest()==digest
 return rom,elf,digest
