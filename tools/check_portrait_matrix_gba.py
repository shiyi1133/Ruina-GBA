"""Original XYZ singles and every supported mixed-sheet palette on actual GBA."""
import hashlib,json,struct,zipfile,zlib,sys
import numpy as np
from PIL import Image
from portrait_assets import logical
from project_env import ARCHIVE,ROOT
from gba_fixture import fixture
from drive_opening import Emulator

def main():
 stress='--stress'in sys.argv;quick='--quick'in sys.argv;video_override=sys.argv[sys.argv.index('--video')+1]if '--video'in sys.argv else None;audio_override=sys.argv[sys.argv.index('--audio')+1]if '--audio'in sys.argv else None
 tracks=json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks'];music=next(t for t in tracks if t['name']=='INT03');effects=sorted((t for t in tracks if t['kind']=='sound'),key=lambda t:-t['frames'])[:3]+[next(t for t in tracks if t['name']=='item_02')];peak=next(r for r in json.loads((ROOT/'evidence/optimization_20261022/music/complete_score_census.json').read_text())['tracks']if r['name']=='INT03'and r['quality']==0)
 (ROOT/'build/portrait_matrix_config.h').write_text('static const int portrait_stress=%d,portrait_quick=%d,portrait_music_id=%d;static const unsigned portrait_music_seek=%d,portrait_effects[4]={%s};\n'%(stress,quick,music['id'],max(0,peak['peak_source_position']-32768),','.join(str(t['id'])for t in effects)))
 native=(ROOT/'build/portraits.bin').read_bytes();h=struct.unpack_from('<5I',native);records=[struct.unpack_from('<HHI',native,h[2]+i*8)for i in range(h[1])];meta=json.loads((ROOT/'build/portraits_manifest.json').read_text());source=[]
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  for sheet in meta['sources']:
   raw=z.read(names[sheet['path']]);w,hh=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);p=np.frombuffer(d[768:],np.uint8).reshape(hh,w);rgb=np.frombuffer(d[:768],np.uint8).reshape(256,3).astype(np.uint16)>>3;pal=rgb[:,0]|(rgb[:,1]<<5)|(rgb[:,2]<<10)
   for i in range(16):source.append((p[i//4*48:i//4*48+48,i%4*48:i%4*48+48],pal))
 for i,r in enumerate(records):
  tiled=np.frombuffer(native,np.uint8,2304,h[4]+r[2]).reshape(3,3,2,2,8,8).transpose(0,2,4,1,3,5).reshape(48,48);assert np.array_equal(tiled,source[i][0]),i
 mixed=(ROOT/'build/portrait_combinations.bin').read_bytes();m=struct.unpack_from('<8I',mixed);assert m[0]==0x50434d52 and m[1]==2;indices=np.frombuffer(mixed,np.dtype('<u2'),m[3],m[4]);cases=[(1<<r[1],[i])for i,r in enumerate(records)]
 for mask,idx in enumerate(indices):
  if not idx:continue
  sheets=[s for s in range(m[2])if mask&(1<<s)];cases.append((mask,[sheets[k%len(sheets)]*16+((mask+k*7)&15)for k in range(4)]))
 if quick:cases=cases[:4]+cases[h[1]:h[1]+40]
 rom,elf,production=fixture('tests/portrait_matrix_diagnostic_gba.c'if '--diagnose'in sys.argv else'tests/portrait_matrix_gba.c','portrait_matrix_stress_quick'if quick else'portrait_matrix_stress'if stress else'portrait_matrix',({**({'video':video_override}if video_override else{}),**({'audio':audio_override}if audio_override else{})}or None));digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/portrait_matrix'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator(rom=rom,elf=elf);rows=[];stream_start=None
 def packed_rgb(colors):return np.stack((colors&31,(colors>>5)&31,(colors>>10)&31),axis=-1).astype(np.uint8)
 try:
  for stage,(mask,faces)in enumerate(cases,1):
   for _ in range(1000):
    if e.debug()[14]==stage:break
    e.frames(1)
   else:raise AssertionError((stage,e.debug()))
   e.frames(2);stream=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16));stream_start=(stream[3]if stress else stream[0])if stream_start is None else stream_start;path=out/'current.png';e.shot(path);screen=np.asarray(Image.open(path).convert('RGB'))>>3;direct=(struct.unpack('<H',e.memory(0x04000000,2))[0]&7)==3;bg=struct.unpack('<H',e.memory(e.symbols['game_palette']+22 if direct else 0x05000016,2))[0];different=0
   for k,i in enumerate(faces):
    p,pal=source[i];expected=pal[p].copy()
    if not direct and mask&(mask-1):
     record=struct.unpack_from('<%dI'%(m[2]+1),mixed,m[5]+(int(indices[mask])-1)*(m[2]+1)*4);palette=np.frombuffer(mixed,np.dtype('<u2'),256,m[6]+record[0]);mapping=np.frombuffer(mixed,np.uint8,256,m[7]+record[records[i][1]+1]);expected=palette[mapping[p]]
    expected[p==0]=bg;actual=screen[24:72,8+k*58:56+k*58];different+=int(np.count_nonzero(np.any(actual!=packed_rgb(expected),axis=2)))
   rows.append({'stage':stage,'sheets_mask':mask,'portraits':faces,'different_pixels':different,'pipeline_diagnostic':list(struct.unpack('<10I',e.memory(e.symbols['portrait_pipeline_diagnostic'],40)))if 'portrait_pipeline_diagnostic'in e.symbols else None})
   if different or stage in(1,49,65,161,170,210,300,400,len(cases)):e.shot(out/f'{stage:03}_sheets{mask:03x}.png')
   if different:raise AssertionError(rows[-1])
   e.frames(2,1);e.frames(2)
  metrics=struct.unpack('<8I',e.memory(e.symbols['video_metrics'],32));rgb_late=struct.unpack('<I',e.memory(e.symbols['balanced_rgb_metrics']+8,4))[0]if direct else 0;result={'status':'pass'if not metrics[5]and not rgb_late and stream[0]==stream_start else'fail','stress_music_plus_four_effects':stress,'quick_subset':quick,'MIDI_underruns_after_priming':stream[0]-stream_start,'original_portrait_bank_size':h[1],'single_original_portraits':sum(len(f)==1 for _,f in cases),'mixed_sheet_combinations':sum(len(f)>1 for _,f in cases),'LCD_faces_checked':sum(len(r['portraits'])for r in rows),'different_pixels':sum(r['different_pixels']for r in rows),'VBlank_commit_overruns':metrics[5],'max_commit_scanlines':metrics[6],'production_rom_sha256':production,'fixture_sha256':digest,'native_bank_sha256':hashlib.sha256(native).hexdigest(),'mixed_bank_sha256':hashlib.sha256(mixed).hexdigest(),'kind':('RGB555 singles and mixed pages each retain original XYZ colors'if direct else'indexed singles retain original colors; mixed pages match explicitly fitted palettes'),'mixed_color_error_report':None if direct else'build/portrait_combinations_manifest.json','direct_RGB555_faces':direct,'RGB_commit_late_chunks':rgb_late if direct else None,'video_source_override':video_override,'audio_source_override':audio_override,'rows':rows,'physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/('latest_stress_subset_attempt.json'if quick else'latest_stress_attempt.json'if stress else'latest_attempt.json')).write_text(json.dumps({'status':result['status'],'report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'},ensure_ascii=False,indent=2));assert result['status']=='pass'
 finally:e.close()

if __name__=='__main__':main()
