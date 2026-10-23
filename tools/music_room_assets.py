"""Keep the original music file names visible in the in-game music room."""
import json
from project_env import ROOT

def main():
 manifest=json.loads((ROOT/'build/audio_manifest.json').read_text());names=[''];replacements=[]
 for track in manifest['tracks']:
  original=track['name'];name=original.encode('gbk','replace').decode('gbk')if track['kind']=='music'else''
  if name and name!=original:replacements.append({'original':original,'display':name})
  names.append(name)
 def literal(s):return '"'+s.replace('\\','\\\\').replace('"','\\"')+'"'
 source='const char *const music_room_names[]={'+','.join(literal(n)for n in names)+'};\n'
 (ROOT/'build/music_room_names.c').write_text(source)
 (ROOT/'build/music_room_names_manifest.json').write_text(json.dumps({'original_music_names':sum(bool(n)for n in names),'display_encoding':'GBK','replacements':replacements},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
