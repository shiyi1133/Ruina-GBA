"""Every original timing event, both playback modes, actual GBA clocks/audio."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from inspect_lcf import data_root,array,integer
from gba_fixture import fixture

def main():
 db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1];cases=[]
 for mode in(0,1):
  for aid,a in array(db[19]):
   n=len(array(a.get(12,b'')));events=[(integer(t.get(1),0)-1,key)for key,t in array(a.get(6,b''))if 1<=integer(t.get(1),0)<=n];events.sort(key=lambda r:r[0]);cases.append((aid,mode,n,[(when<<16)|key for when,key in events]))
 generated=ROOT/'build/fixtures/animation_timing';generated.mkdir(parents=True,exist_ok=True);(ROOT/'build/animation_timing_cases.h').write_text('static const int timing_cases[][2]={'+','.join('{%d,%d}'%r[:2]for r in cases)+'};\n');override=generated/'battle.c';override.write_text((ROOT/'runtime/rm2k/battle.c').read_text()+'\n'+(ROOT/'tests/battle_animation_target_setup.inc').read_text());rom,elf,digest=fixture('tests/animation_timing_gba.c','animation_timing',{'battle':str(override)});e=Emulator(rom=rom,elf=elf);rows=[];out=ROOT/'evidence/animation_smooth_20261023'
 def until(stage):
  for _ in range(6000):
   d=e.debug();assert d[0]!=0x4641554c,d
   if d[18]==stage:return
   e.frames(4)
  raise AssertionError(('timing stage timeout',stage,e.debug()))
 try:
  until(1);base=e.command('lcdrgbhash');e.frames(2,1);e.frames(2)
  for i,(aid,mode,n,expected)in enumerate(cases):
   until(100+i);e.frames(2);timing=list(struct.unpack('<8I',e.memory(e.symbols['animation_timing_debug'],32)));order=list(struct.unpack('<32I',e.memory(e.symbols['animation_sound_order'],128)))[:timing[3]];before,after=struct.unpack('<2I',e.memory(e.symbols['timing_case_audio'],8))
   assert timing[0]==aid and timing[4]==n*2 and timing[7]==mode,(i,timing)
   assert order==expected,(i,aid,mode,order,expected)
   assert after==before,('MIDI underrun',i,after-before)
   assert e.command('lcdrgbhash')==base,('unclean restoration',i,aid,mode)
   if mode:assert timing[2]==n and timing[1]==0,(i,timing,n)
   peak_ticks=struct.unpack('<I',e.memory(e.symbols['animation_render_trace']+40,4))[0];peak_hardware_frames=(peak_ticks*1024+280895)//280896
   if not mode and n:assert timing[2]+timing[1]==n and n*2<=timing[6]-timing[5]<=n*2+3*peak_hardware_frames+8,(i,timing,n,peak_hardware_frames)
   rows.append({'animation':aid,'mode':mode,'source_frames':n,'presented':timing[2],'omitted_transitions':timing[1],'timing_events':order,'hardware_ticks_after_preparation':timing[6]-timing[5]if not mode and n else None,'maximum_draw_hardware_frames_ceiling':peak_hardware_frames,'MIDI_underruns':after-before});e.frames(2,1);e.frames(2)
   if i%20==0:print('Checked',i+1,'/',len(cases),'animation/mode pairs',flush=True)
  r={'status':'pass','production_ROM_sha256':digest,'fixture_ROM_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'animation_records':len(cases)//2,'playback_modes':2,'cases':rows,'all_original_timing_events_in_order_once':True,'clean_restoration_after_every_case':True,'no_MIDI_queue_underruns':True,'scope':'All original animation records in separately linked controlled battle with live MIDI/SFX, real frame clock and buttons. Original-time mode may omit late transition images; full-frames mode checks every source frame. Not campaign or physical hardware acceptance.','physical_hardware':'not_run'};(out/'timing_all.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in r.items()if k!='cases'},ensure_ascii=False,indent=2))
 except Exception as error:(out/'timing_all_failure.json').write_text(json.dumps({'status':'fail','production_ROM_sha256':digest,'completed_cases':len(rows),'error':repr(error)},indent=2));raise
 finally:e.close()
if __name__=='__main__':main()
