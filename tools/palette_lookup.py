"""ROM-only RGB555 to indexed-palette lookup for uniform alpha and tint."""
import hashlib,json,re
from project_env import ROOT

def main():
 text=(ROOT/'build/assets.c').read_text();match=re.search(r'game_palette\[256\]\s*=\s*\{([^}]+)\}',text);assert match
 palette=[int(x)for x in match.group(1).split(',')if x.strip()];assert len(palette)==256
 digest=hashlib.sha256(bytes(v for c in palette for v in (c&255,c>>8))).hexdigest()
 target=ROOT/'build/palette_lookup.bin';meta=ROOT/'build/palette_lookup_manifest.json'
 if target.exists()and meta.exists():
  old=json.loads(meta.read_text())
  if old['palette_sha256']==digest and target.stat().st_size==32768 and hashlib.sha256(target.read_bytes()).hexdigest()==old['table_sha256']:return
 colors=[(c&31,(c>>5)&31,(c>>10)&31)for c in palette];result=bytearray(32768)
 for rgb in range(32768):
  r,g,b=rgb&31,(rgb>>5)&31,(rgb>>10)&31;best=0;distance=999999
  for i,(rr,gg,bb)in enumerate(colors):
   score=(r-rr)**2+(g-gg)**2+(b-bb)**2
   if score<distance:distance=score;best=i
  result[rgb]=best
 target.write_bytes(result);meta.write_text(json.dumps({'palette_sha256':digest,'table_sha256':hashlib.sha256(result).hexdigest(),'bytes':len(result),'mapping':'nearest squared RGB555 distance, first palette entry on ties','RAM_bytes':0},indent=2))
 print(json.dumps({'RGB555_lookup_bytes':len(result),'RAM_bytes':0}))

if __name__=='__main__':main()
