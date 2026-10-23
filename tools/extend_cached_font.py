"""Add missing UI glyphs to the converted font without reconverting images.

Full assets.py already collects UI source text. This small helper performs the
same 12px glyph generation for an otherwise cached incremental asset build.
Existing glyph rows and every image byte remain unchanged.
"""
import argparse, hashlib, json, re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from project_env import ROOT, FONT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('text_files', nargs='+')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    source = ROOT / 'build/assets.c'
    original = source.read_text()
    codes_pattern = r'const unsigned short glyph_codes\[[^]]*\]\s*=\s*\{([^}]+)\};'
    rows_pattern = r'const unsigned short glyph_rows\[\]\[12\]\s*=\s*\{(.*?)\};'
    cm = re.search(codes_pattern, original)
    rm = re.search(rows_pattern, original, re.S)
    assert cm and rm
    codes = [int(x, 0) for x in cm.group(1).split(',') if x.strip()]
    rows = [[int(x, 0) for x in row.split(',')] for row in re.findall(r'\{([^{}]+)\}', rm.group(1))]
    assert len(codes) == len(rows) and all(len(row) == 12 for row in rows)
    old = dict(zip(codes, rows))
    assert len(old) == len(codes) and codes == sorted(codes)
    requested = set(''.join((ROOT / p).read_text() for p in args.text_files))
    additions = {}
    font = ImageFont.truetype(str(FONT), 12)
    for c in requested:
        if ord(c) < 32:
            continue
        try:
            encoded = c.encode('gbk')
        except UnicodeEncodeError:
            continue
        if not 1 <= len(encoded) <= 2:
            continue
        code = int.from_bytes(encoded, 'big')
        if code in old:
            continue
        im = Image.new('1', (12, 12))
        ImageDraw.Draw(im).text((0, -1), c, font=font, fill=1)
        glyph = [sum(1 << (11 - x) for x in range(12) if im.getpixel((x, y))) for y in range(12)]
        assert any(glyph), ('empty glyph', c)
        additions[code] = (c, glyph)
    merged = {**old, **{code: row for code, (_, row) in additions.items()}}
    keys = sorted(merged)
    codes_c = 'const unsigned short glyph_codes[%d]={%s};' % (len(keys), ','.join(map(str, keys)))
    rows_c = 'const unsigned short glyph_rows[][12]={' + ','.join('{' + ','.join(map(str, merged[k])) + '}' for k in keys) + '};'
    updated = re.sub(codes_pattern, lambda _: codes_c, original, count=1)
    updated = re.sub(rows_pattern, lambda _: rows_c, updated, count=1, flags=re.S)
    # Strip the two arrays and prove all non-font data remained byte-identical.
    strip = lambda s: re.sub(rows_pattern, '', re.sub(codes_pattern, '', s, count=1), count=1, flags=re.S)
    assert strip(updated) == strip(original)
    assert all(merged[c] == row for c, row in old.items())
    source.write_text(updated)
    header = ROOT / 'build/assets.h'
    header.write_text(re.sub(r'#define GLYPH_COUNT \d+', '#define GLYPH_COUNT %d' % len(keys), header.read_text()))
    manifest = ROOT / 'build/asset_manifest.json'
    meta = json.loads(manifest.read_text());meta['glyph_count'] = len(keys)
    manifest.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    report = {'status': 'pass', 'original_glyphs': len(old), 'current_glyphs': len(keys),
              'added': [{'character': additions[k][0], 'GBK_code': k} for k in sorted(additions)],
              'existing_glyph_rows_unchanged': True, 'non_font_asset_data_unchanged': True,
              'font_sha256': hashlib.sha256(FONT.read_bytes()).hexdigest(),
              'assets_c_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    out = ROOT / args.report;out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
