"""Actual credits-page input, unchanged title artwork and normal new game."""
import hashlib,json,re,struct
from pathlib import Path
from drive_opening import ROOT,Emulator
from check_save import opening

def main():
    rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023'/digest[:12]/'attribution';out.mkdir(parents=True,exist_ok=True)
    text='胖胖&咩咩 移植';source=(ROOT/'build/assets.c').read_text();match=re.search(r'const unsigned short glyph_codes\[[^]]*\]\s*=\s*\{([^}]+)\};',source)
    codes={int(x,0)for x in match.group(1).split(',')if x.strip()}
    assert all(int.from_bytes(c.encode('gbk'),'big')in codes for c in text)
    previous=ROOT/'history/balanced_optimization_20261023/production_6e70c2dc0b4c/build'
    # A portable source ZIP omits previous ROMs. The exact prior-title LCD
    # comparison additionally runs when the local pre-attribution snapshot exists.
    old_hash=None
    if(previous/'废都物语_GBA_开篇开发验证版.gba').exists():
        e=Emulator(rom=previous/'废都物语_GBA_开篇开发验证版.gba',elf=previous/'ruina_opening_dev.elf')
        try:e.frames(180);old_hash=e.command('lcdhash');e.shot(out/'previous_title.png')
        finally:e.close()
    e=Emulator()
    try:
        e.frames(180);current=e.command('lcdhash');e.shot(out/'title.png')
        if old_hash:assert old_hash==current,('title artwork changed',old_hash,current)
        e.key(1);e.key(128);e.key(128);e.shot(out/'menu_entry.png');e.key(1)
        assert e.debug()[15]==1,e.debug()
        shown=e.memory(e.symbols['dialog'],8192).split(b'\0',1)[0].decode('gbk')
        assert shown.startswith(text+'\n')and'原作：枯草章吉'in shown,shown
        assert shown.count(text)==1
        e.shot(out/'credits.png');e.key(1);e.frames(180);assert e.command('lcdhash')==current
        opening(e,1);assert e.debug()[15]==4,e.debug();e.shot(out/'new_game_after_credits.png')
        commands=e.log.copy()
    finally:e.close()
    result={'status':'pass','ROM_sha256':digest,'attribution':text,'location':'制作信息 menu page only; no extra title-art text','all_credit_glyphs_present':True,'credits_text':shown,'title_LCD_hash':current,'prior_title_LCD_hash':old_hash,'prior_title_comparison':'exact'if old_hash else'not_run; prior ROM absent in portable source package','credits_closed_to_title':True,'new_game_after_credits_reaches_map':True,'commands':commands,'hardware':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
