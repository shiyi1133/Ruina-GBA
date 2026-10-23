"""Rebuild the current simplified audio profile without historical work folders.
Requires NumPy, the cached original event exports and the original SoundFont.
The existing audio index is the stable resource-ID template. WAV payloads are
retained exactly; run pcm_audio_assets separately to reconvert original WAVs.
"""
import hashlib,json,shutil,subprocess,sys
from project_env import ROOT

def main():
 paths=[ROOT/'build/audio.bin',ROOT/'build/native_music/native_soundfont.bin'];before={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths};subprocess.run([sys.executable,'tools/light_music_assets.py'],cwd=ROOT,check=True)
 for name,target in[('audio.bin',paths[0]),('audio_manifest.json',ROOT/'build/audio_manifest.json'),('native_soundfont.bin',paths[1])]:shutil.copy2(ROOT/'build/light_music'/name,target)
 subprocess.run([sys.executable,'tools/scaled_music_assets.py'],cwd=ROOT,check=True);after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths};report={'status':'rebuilt','historical_work_folders_required':False,'before':before,'after':after,'same_input_byte_identical':before==after};out=ROOT/'build/simplified_audio_rebuild.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
