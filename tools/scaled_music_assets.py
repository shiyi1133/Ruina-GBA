"""Compile wavetable amplitude steps once, removing per-sample ARM7 multiplies.
Both modes retain the original 16384 Hz score clock. Playback mixes paired
samples; the music room keeps finer 128-point waves and original stereo pan,
while gameplay uses coarse 32-point mono waves. No score event is discarded.
"""
import array,hashlib,json,struct,sys
from pathlib import Path
from project_env import ROOT

def main():
 path=ROOT/'build/native_music/native_soundfont.bin';raw=path.read_bytes();h=list(struct.unpack_from('<8I',raw));assert h[0]==0x3146534c and h[1]in(1,2)
 base=bytearray(raw[:h[2]]if h[1]==2 else raw);samples=struct.unpack_from('<32768b',base,h[3])
 # Keep cached-source builds dependency-free. These products fit signed16;
 # the iteration order and bytes match the previous NumPy table exactly.
 values=array.array('h',(samples[program*256+point*2]*level for program in range(128)for level in range(65)for point in range(128)))
 if sys.byteorder!='little':values.byteswap()
 table=values.tobytes();offset=(len(base)+3)&~3;base.extend(bytes(offset-len(base)));h[1]=2;h[2]=offset;struct.pack_into('<8I',base,0,*h);bank=bytes(base)+table
 path.write_bytes(bank);(ROOT/'build/light_music/native_soundfont.bin').write_bytes(bank)
 report={'format':'128 original-derived periodic programs, 65 compiled amplitude steps, 128 points; gameplay samples 32 points','bytes':len(bank),'table_bytes':len(table),'additional_samples_per_mix':2,'score_clock_Hz':16384,'music_room':'fine stereo wavetable, paired samples','gameplay':'coarse mono wavetable, paired samples','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bank_sha256':hashlib.sha256(bank).hexdigest()};(ROOT/'build/scaled_music_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
