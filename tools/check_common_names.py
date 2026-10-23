"""Real naming buttons, glyph pixels, editing limits and default-name paths."""
import argparse,hashlib, json, re, struct
from pathlib import Path
import numpy as np
from PIL import Image
from drive_opening import ROOT, Emulator


def main():
    p=argparse.ArgumentParser();p.add_argument('--rom');p.add_argument('--elf');args=p.parse_args()
    rom = Path(args.rom).resolve()if args.rom else ROOT / 'build/废都物语_GBA_开篇开发验证版.gba'
    elf = Path(args.elf).resolve()if args.elf else ROOT / 'build/ruina_opening_dev.elf'
    digest = hashlib.sha256(rom.read_bytes()).hexdigest()
    out = ROOT / 'evidence/name_input_v062' / digest[:12]
    out.mkdir(parents=True, exist_ok=True)
    text = (ROOT / 'platform/gba/event_input.c').read_text()
    pools = [re.search(r'name_' + key + r'\[\]="([^"]+)"', text).group(1) for key in ('surnames', 'given')]
    assert list(map(len, pools)) == [20, 30]
    assets = (ROOT / 'build/assets.c').read_text()
    codes = [int(x) for x in re.search(r'glyph_codes\[[^]]+\]=\{([^}]+)\}', assets).group(1).split(',')]
    rows = [[int(x) for x in row.split(',')] for row in re.findall(r'\{([^{}]+)\}', re.search(r'glyph_rows\[\]\[12\]=\{(.*?)\};', assets, re.S).group(1))]
    glyphs = dict(zip(codes, rows))
    checks, processes = [], []

    def reach():
        e = Emulator(rom=rom,elf=elf);e.frames(30);e.key(1);e.key(1);e.frames(150);picked = False
        for _ in range(150):
            d = e.debug();assert d[0] != 0x4641554c and d[15] != 5, d
            if d[15] == 3:
                return e
            if d[15] == 1:
                e.key(1)
            elif d[15] == 2:
                if d[22] == 1 and not picked:
                    e.key(128);picked = True  # knight's child
                e.key(1)
            else:
                e.frames(120)
        e.close();raise AssertionError('name screen not reached')

    def actual_name(e, actor):
        return e.memory(e.symbols['game'] + 4068 + actor * 196, 32).split(b'\0', 1)[0].decode('gbk')

    def close(e):
        processes.append(e.log.copy());e.close()

    e = reach()
    try:
        actor = e.debug()[16];original = actual_name(e, actor)
        for page, key in enumerate((512, 256)):
            e.key(key);e.frames(2);d = e.debug()
            assert (d[17], d[18], d[19]) == (page, 0, len(pools[page])), d
            p = out / ('common_surnames.png' if page == 0 else 'given_name_characters.png')
            e.shot(p);pixels = np.asarray(Image.open(p).convert('RGB')) >> 3
            mode=struct.unpack('<H',e.memory(0x04000000,2))[0]&7
            palette = struct.unpack('<16H', e.memory(e.symbols['game_palette']if mode==3 else 0x05000000, 32))
            differences = []
            for i, char in enumerate(pools[page]):
                code = int.from_bytes(char.encode('gbk'), 'big');assert code in glyphs, char
                color = palette[2 if i == 0 else 1]
                rgb = np.array((color & 31, color >> 5 & 31, color >> 10 & 31))
                x, y = 14 + i % 10 * 22, 57 + i // 10 * 20
                observed = np.all(pixels[y:y+12, x:x+12] == rgb, axis=2)
                expected = np.array([[(row >> (11 - x)) & 1 for x in range(12)] for row in glyphs[code]], dtype=bool)
                differences.append(int(np.count_nonzero(observed != expected)))
            assert not any(differences), (page, differences)
            checks.append({'check': 'all selectable characters render as their exact cached glyphs', 'page': page, 'characters': len(pools[page]), 'different_pixels': sum(differences), 'pass': True})
            for key, wanted in ((32, len(pools[page])-1), (128, 9), (64, len(pools[page])-1), (16, 0)):
                e.key(key);assert e.debug()[18] == wanted, e.debug()
        checks.append({'check': 'both grid pages wrap without selecting blank cells', 'pass': True})
        # First selection starts a fresh name, and length remains six GBK characters.
        e.key(256)
        for _ in range(7):
            e.key(1)
        assert e.debug()[20] == 12, e.debug()
        e.key(2);assert e.debug()[20] == 10, e.debug()
        e.key(4);assert e.debug()[20] == len(original.encode('gbk')) and e.debug()[23] == 0, e.debug()
        checks.append({'check': 'six-character bound, whole-character deletion and SELECT restore', 'pass': True})
        e.key(512)
        for _ in range(3):
            e.key(16)
        assert pools[0][e.debug()[18]] == '刘'
        e.key(1)
        assert (e.debug()[17], e.debug()[18], e.debug()[20]) == (1, 0, 2), e.debug()
        for _ in range(5):
            e.key(16)
        assert pools[1][e.debug()[18]] == '轩'
        e.key(1);e.shot(out / 'custom_name_liuxuan.png')
        e.key(8)
        assert actual_name(e, actor) == '刘轩', actual_name(e, actor)
        checks.append({'check': 'surname starts a new name, auto-opens given names, and confirms the exact name', 'confirmed_name': '刘轩', 'pass': True})
    finally:
        close(e)
    e = reach()
    try:
        actor = e.debug()[16];original = actual_name(e, actor);e.key(8)
        assert actual_name(e, actor) == original
        checks.append({'check': 'START directly preserves the original name', 'pass': True})
    finally:
        close(e)
    e = reach()
    try:
        actor = e.debug()[16];original = actual_name(e, actor)
        for _ in range(16):
            if not e.debug()[20]:
                break
            e.key(2)
        assert e.debug()[20] == 0, e.debug()
        e.key(8);assert actual_name(e, actor) == original
        checks.append({'check': 'empty confirmation keeps the original name rather than writing a blank actor name', 'pass': True})
    finally:
        close(e)
    result = {'status': 'pass', 'rom_sha256': digest, 'surnames': pools[0], 'given_name_characters': pools[1],
              'checks': checks, 'input': 'real production ROM new-game buttons', 'memory': 'read only',
              'emulator_states': False, 'hardware': 'not_run', 'commands': processes}
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (out.parent / 'latest_attempt.json').write_text(json.dumps({'status': 'pass', 'report': str((out / 'result.json').relative_to(ROOT))}, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k != 'commands'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
