"""Observe every hardware frame after real name completion, not key() skips."""
import hashlib,json,struct,sys
from PIL import Image
from drive_opening import ROOT,Emulator

def run(origin):
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()
 out=ROOT/'evidence/naming_cut'/digest[:12]/f'origin_{origin}';out.mkdir(parents=True,exist_ok=True)
 e=Emulator();rows=[];captures=[];tones=set();alphas=set();last=None;reached=False;black_samples=[];cut_age=0
 try:
  e.frames(30);e.key(1);e.key(1);e.frames(150);picked=False
  for _ in range(150):
   d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
   if d[15]==3:break
   if d[15]==1:e.key(1)
   elif d[15]==2:
    if d[22]==1 and not picked:
     for _ in range({3:0,1:1,2:2,4:3}[origin]):e.key(128)
     picked=True
    e.key(1)
   else:e.frames(120)
  else:raise AssertionError('name input not reached')
  e.frames(2);e.shot(out/'name_entry.png')
  cooldown=0;press=0;started=False;world_frames=0
  for frame in range(12000):
   d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
   g=e.symbols['game']
   tone=tuple(e.memory(g+39650,4));remaining=struct.unpack('<H',e.memory(g+39700,2))[0]
   pic=e.memory(g+35716+5*30,30);alpha=pic[20];active=struct.unpack_from('<h',pic)[0]>=0
   ready=struct.unpack('<I',e.memory(e.symbols['ui_ready'],4))[0]
   cut=struct.unpack('<I',e.memory(e.symbols['cut_active'],4))[0]
   cut_age=cut_age+1 if cut else 0
   if cut_age==3:
    name=f'black_{frame:05d}.png';e.shot(out/name);captures.append(name)
    black_samples.append(Image.open(out/name).convert('RGB').getbbox()is None)
   map_id=struct.unpack('<i',e.memory(g+29768,4))[0]
   mode=d[15];tones.add(tone)
   if active:alphas.add(alpha)
   signature=(mode,d[5],d[6],d[7],d[8],map_id,tone,remaining,alpha if active else -1)
   if signature!=last:
    rows.append({'frame':frame,'mode':mode,'opcode':d[5],'common':d[6],'event':d[7],'offset':d[8],'map':map_id,'tone':tone,'tone_remaining':remaining,'picture5_alpha':alpha if active else None})
    # Preserve visible evidence of tone and alpha changes, including the old
    # failed candidate. This is read-only; no emulated state is injected.
    if last is None or signature[6:]!=last[6:]:
     name=f'frame_{frame:05d}.png';e.shot(out/name);captures.append(name)
    last=signature
   if mode!=3:started=True
   if mode==4 and ready:
    world_frames+=1
    if world_frames>=3:reached=True;break
   else:world_frames=0
   key=0
   if press: key=press;press=0
   elif cooldown:cooldown-=1
   elif ready and (mode==3 and not started or mode in(1,2)):
    # START completes the original name screen; A accepts original dialogue
    # and the "story begins" choice. Every pressed/released frame is sampled.
    key=8 if mode==3 else 1;press=key;cooldown=24
   e.frames(1,key)
  checks={'original_name_completed':started,'original_opening_reaches_cave':reached and map_id==23,
          'screen_tones_have_no_intermediate_fade':tones<= {(100,100,100,100),(0,0,0,30)},
          'picture5_has_only_cut_opacity':alphas<={0,100},
          'no_screen_tone_animation_running':not any(r['tone_remaining']for r in rows),
          'original_picture_fade_endpoint_reached':100 in alphas,
          'original_cave_tone_endpoint_reached':any(r['map']==23 and r['tone']==(100,100,100,100)for r in rows),
          'actual_new_image_preparation_hidden_by_black':bool(black_samples)and all(black_samples)}
  e.frames(2);e.shot(out/'cave.png')
  report={'status':'pass'if all(checks.values())else'fail','rom_sha256':digest,'origin':origin,
          'method':'production ROM; real new-game buttons; every hardware frame observed from name completion through cave entry',
          'checks':checks,'black_preparation_samples':black_samples,'screen_tones':sorted(tones),'picture5_opacities':sorted(alphas),'trace':rows,'captures':captures,
          'memory_writes':False,'instant_states':False,'hardware':'not_run','commands':e.log}
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
  print(json.dumps({k:v for k,v in report.items()if k not in('commands','trace','captures')},ensure_ascii=False),flush=True)
  return report,str((out/'result.json').relative_to(ROOT))
 finally:e.close()

def main():
 reports=[run(int(n))for n in sys.argv[1:]or ['1']]
 combined={'status':'pass'if all(r['status']=='pass'for r,_ in reports)else'fail',
           'rom_sha256':reports[0][0]['rom_sha256'],'origins':[{'origin':r['origin'],'status':r['status'],'report':p}for r,p in reports]}
 out=ROOT/'evidence/naming_cut'/combined['rom_sha256'][:12]/'result.json';out.write_text(json.dumps(combined,ensure_ascii=False,indent=2))
 (out.parent.parent/'latest_attempt.json').write_text(json.dumps({'report':str(out.relative_to(ROOT)),'status':combined['status']},ensure_ascii=False,indent=2))
 assert combined['status']=='pass',combined

if __name__=='__main__':main()
