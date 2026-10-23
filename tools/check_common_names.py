"""Actual naming UI: every selectable glyph, paging, mixed editing and SRAM."""
import argparse, ast, hashlib, json, re, struct
from pathlib import Path
import numpy as np
from PIL import Image
from drive_opening import ROOT, Emulator
from response_meter import ResponseMeter
from save_observation import save_payload, check_load

KEYS = ('surnames', 'given', 'upper', 'lower', 'symbols', 'digits')


def reach_name(e):
    e.frames(30); e.key(1); e.key(1); e.frames(150); picked = False
    for _ in range(150):
        d = e.debug(); assert d[0] != 0x4641554c and d[15] != 5, d
        if d[15] == 3: return
        if d[15] == 1: e.key(1)
        elif d[15] == 2:
            if d[22] == 1 and not picked: e.key(128); picked = True
            e.key(1)
        else: e.frames(120)
    raise AssertionError('name screen not reached')


def actual_name(e, actor):
    return e.memory(e.symbols['game'] + 4068 + actor * 196, 32).split(b'\0', 1)[0].decode('gbk')


def pools_from_source():
    text = (ROOT / 'platform/gba/event_input.c').read_text()
    return [ast.literal_eval('"' + re.search(r'name_' + key + r'\[\]="((?:\\.|[^"\\])*)"', text).group(1) + '"') for key in KEYS]


def glyphs_from_cache():
    assets = (ROOT / 'build/assets.c').read_text()
    codes = [int(x) for x in re.search(r'glyph_codes\[[^]]+\]=\{([^}]+)\}', assets).group(1).split(',')]
    rows = [[int(x) for x in row.split(',')] for row in re.findall(r'\{([^{}]+)\}', re.search(r'glyph_rows\[\]\[12\]=\{(.*?)\};', assets, re.S).group(1))]
    return dict(zip(codes, rows))


def go(e, category, index=0):
    # Shoulder switches deliberately reset to the first character.
    if e.debug()[17] == category: e.key(256); e.key(512)
    else:
        while e.debug()[17] != category: e.key(256)
    assert e.debug()[18] == 0, e.debug()
    for _ in range(index // 10): e.key(128)
    for _ in range(index % 10): e.key(16)
    assert e.debug()[18] == index, e.debug()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--rom'); p.add_argument('--elf'); args = p.parse_args()
    rom = Path(args.rom).resolve() if args.rom else ROOT / 'build/废都物语_GBA_开篇开发验证版.gba'
    elf = Path(args.elf).resolve() if args.elf else ROOT / 'build/ruina_opening_dev.elf'
    digest = hashlib.sha256(rom.read_bytes()).hexdigest()
    out = ROOT / 'evidence/ui_v071' / digest[:12] / 'naming'; out.mkdir(parents=True, exist_ok=True)
    pools = pools_from_source(); glyphs = glyphs_from_cache()
    assert list(map(len, pools[:4])) == [30, 100, 26, 26]
    assert pools[2] == 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and pools[3] == 'abcdefghijklmnopqrstuvwxyz'
    assert pools[5] == '0123456789' and len(pools[4]) >= 20
    assert all(len(set(s)) == len(s) for s in pools)
    assert not any(c in ''.join(pools) for c in ('$', '\\', '/'))
    checks, processes = [], []
    e = Emulator(rom=rom, elf=elf)
    try:
        reach_name(e); actor = e.debug()[16]; original = actual_name(e, actor); meter = ResponseMeter(e)
        for category, pool in enumerate(pools):
            go(e, category)
            assert e.debug()[19] == len(pool), e.debug()
            for top in range(0, len(pool), 30):
                if top:
                    for _ in range(3): e.key(128)
                assert e.debug()[18] == top, e.debug()
                image = out / f'{KEYS[category]}_{top//30+1}.png'; e.shot(image)
                pixels = np.asarray(Image.open(image).convert('RGB')) >> 3
                palette = struct.unpack('<16H', e.memory(e.symbols['game_palette'], 32))
                differences = []
                for i in range(top, min(top + 30, len(pool))):
                    char = pool[i]; code = int.from_bytes(char.encode('gbk'), 'big'); assert code in glyphs, char
                    color = palette[2 if i == top else 1]
                    rgb = np.array((color & 31, color >> 5 & 31, color >> 10 & 31))
                    x = (17 if ord(char) < 128 else 14) + i % 30 % 10 * 22
                    y = 57 + i % 30 // 10 * 20
                    observed = np.all(pixels[y:y+12, x:x+12] == rgb, axis=2)
                    expected = np.array([[(row >> (11 - j)) & 1 for j in range(12)] for row in glyphs[code]], dtype=bool)
                    differences.append(int(np.count_nonzero(observed != expected)))
                assert not any(differences), (category, top, differences)
                checks.append({'check':'LCD selectable glyphs match cache exactly', 'category':KEYS[category], 'page':top//30+1, 'characters':len(differences), 'different_pixels':sum(differences), 'pass':True})
            go(e, category)
            for key, expected in ((32,len(pool)-1),(128,9),(64,len(pool)-1),(16,0)):
                e.key(key); assert e.debug()[18] == expected, e.debug()
        checks.append({'check':'all six categories wrap without selecting empty cells', 'pass':True})
        go(e, 1, 29)
        meter.action('given_next_page_right',16); assert e.debug()[18] == 30
        meter.action('given_previous_page_left',32); assert e.debug()[18] == 29
        go(e, 1)
        before = struct.unpack('<4I', e.memory(e.symbols['balanced_name_metrics'], 16))
        meter.action('name_cell_right',16); meter.action('name_cell_left',32)
        after = struct.unpack('<4I', e.memory(e.symbols['balanced_name_metrics'], 16))
        assert after[0:2] == before[0:2] and after[2]-before[2] == 4, (before,after)
        meter.action('category_next',256); meter.action('category_previous',512)
        checks.append({'check':'cursor redraws only two cells; all measured changes commit complete nonblack LCD frames', 'pass':True})
        for category, byte_count in ((1,12),(2,6)):
            go(e, category); e.key(4)
            for _ in range(7): e.key(1)
            assert e.debug()[20] == byte_count, e.debug()
            e.key(2); assert e.debug()[20] == byte_count-(2 if category == 1 else 1), e.debug()
        e.key(4); assert e.debug()[20] == len(original.encode('gbk')) and e.debug()[23] == 0
        checks.append({'check':'six characters for both ASCII and Chinese, complete deletion and SELECT original restore', 'pass':True})
        wanted = '刘aZ9·慧'
        def enter_mixed():
            e.key(4)
            for char in wanted:
                category = next(i for i,s in enumerate(pools) if char in s)
                go(e, category, pools[category].index(char)); e.key(1)
        enter_mixed(); assert e.debug()[20] == len(wanted.encode('gbk'))
        # Delete two-byte final characters and a one-byte digit in one name.
        for prefix in ('刘aZ9·','刘aZ9','刘aZ'):
            e.key(2); assert e.debug()[20] == len(prefix.encode('gbk')), e.debug()
        enter_mixed(); go(e, 2, 1); e.key(1)
        assert e.debug()[20] == len(wanted.encode('gbk')), 'seventh mixed character accepted'
        e.shot(out/'mixed_name.png'); e.key(8)
        assert actual_name(e,actor) == wanted, actual_name(e,actor)
        for _ in range(180):
            d=e.debug(); assert d[0] != 0x4641554c and d[15] != 5,d
            if d[15] == 4: break
            if d[15] in (1,2): e.key(1)
            else: e.frames(120)
        else: raise AssertionError('mixed name did not reach map')
        e.key(2); e.key(1); e.shot(out/'mixed_name_status.png'); e.key(2)
        e.key(2); e.key(128); e.key(128); e.key(1)
        assert e.debug()[15] == 1, e.debug()
        save=out/'mixed_name.sav'; assert e.command('savecopy '+str(save)).startswith('SAVE ')
        version,payload=save_payload(save.read_bytes()); assert version==5 and len(payload)==39704
        assert e.memory(e.symbols['game'],len(payload))==payload
        checks.append({'check':'mixed case, Chinese, digit and symbol saved by real game menu with unchanged v5 format', 'name':wanted,'pass':True})
        responses=meter.samples
    except Exception as error:
        e.shot(out/'failure.png'); (out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'debug':e.debug(),'checks':checks,'commands':e.log},ensure_ascii=False,indent=2)); raise
    finally: processes.append(e.log.copy()); e.close()
    e=Emulator(save=save,rom=rom,elf=elf)
    try:
        e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240)
        assert e.debug()[15] == 4 and actual_name(e,actor) == wanted,e.debug()
        load=check_load(e,payload); e.shot(out/'mixed_name_cold_load.png')
        checks.append({'check':'new emulator process cold loads the exact mixed name and persistent player state','pass':True,'observations':load})
    finally: processes.append(e.log.copy());e.close()
    for empty in (False,True):
        e=Emulator(rom=rom,elf=elf)
        try:
            reach_name(e);actor=e.debug()[16];original=actual_name(e,actor)
            if empty:
                while e.debug()[20]:e.key(2)
            e.key(8);assert actual_name(e,actor)==original
            checks.append({'check':'empty confirmation keeps original' if empty else 'START keeps default without editing','pass':True})
        finally:processes.append(e.log.copy());e.close()
    result={'status':'pass','rom_sha256':digest,'pools':dict(zip(KEYS,pools)),'counts':dict(zip(KEYS,map(len,pools))), 'checks':checks,'response_samples':responses,'commands':processes,'memory':'read only','emulator_states':False,'hardware':'not_run','full_campaign':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    (ROOT/'evidence/ui_v071/naming_latest.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('commands','response_samples')},ensure_ascii=False,indent=2))

if __name__ == '__main__':main()
