"""Independent old/new audio sources, identical immutable banks and IRQ inputs."""
import hashlib,json,subprocess
from project_env import ROOT

def main():
 old=ROOT/'tests/reference/audio_pre_voice_metadata.c';current=ROOT/'platform/gba/audio.c';bindings={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in[old,current,ROOT/'runtime/rm2k/light_midi.c',ROOT/'runtime/rm2k/native_midi.h',ROOT/'build/audio.bin',ROOT/'build/native_music/native_soundfont.bin']};out=ROOT/'evidence/optimization_20261022/audio_irq';out.mkdir(exist_ok=True);all_rows=[]
 for name,source in[('before',old),('after',current)]:
  target=ROOT/'build'/('audio_irq_'+name+'_host');subprocess.run(['cc','-std=c99','-O2','-ffreestanding','-fno-builtin','-fdata-sections','-ffunction-sections','-Wl,--gc-sections','-DRUINA_LIGHT_MUSIC','-DRUINA_PCM_WAV','-DAUDIO_SOURCE="'+str(source)+'"','-Isource','-Iruntime/rm2k','-Iplatform/gba','tests/audio_irq_parity_host.c','runtime/rm2k/light_midi.c','-o',str(target)],cwd=ROOT,check=True);p=subprocess.run([str(target)],capture_output=True,text=True,cwd=ROOT);assert p.returncode==0,(p.returncode,p.stderr);rows=json.loads(p.stdout);(out/(name+'.json')).write_text(json.dumps(rows,indent=2));all_rows.append(rows)
 assert all_rows[0]==all_rows[1],[(a,b)for a,b in zip(*all_rows)if a!=b][:5]
 report={'status':'pass','scope':'host FIFO arithmetic parity, all 323 audio IDs, pitches50/100/150/200, MIDI modes, four simultaneous effects, gain/pan changes, pause/resume; separate GBA timing tests required','cases':len(all_rows[0]),'FIFO_words_compared':sum(r['FIFO_words']for r in all_rows[0]),'source_sha256':bindings};(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
