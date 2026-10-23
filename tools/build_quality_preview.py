"""Separate RGB555 opening target; never replace the v0.6.2 playable ROM."""
import hashlib, json
from pathlib import Path
from gba_fixture import fixture
from project_env import ROOT


def main():
    rom, elf, baseline = fixture('experiments/quality_preview/main.c', 'quality_preview', {
        'video': 'experiments/quality_preview/video.c',
        'ruina_adapter': 'experiments/quality_preview/adapter.c',
        'pictures': 'experiments/quality_preview/pictures.c',
        'dialog': 'experiments/quality_preview/dialog.c',
        'event_input': 'experiments/quality_preview/event_input.c',
        'world': 'experiments/quality_preview/world.c',
        'save': 'experiments/quality_preview/save.c'})
    raw = bytearray(rom.read_bytes());raw[160:172] = b'RUINA RGB555';raw[172:176] = b'RUQI'
    raw[189] = (-sum(raw[160:189]) - 0x19) & 255
    raw += b'\xff' * (-len(raw) % 4)
    assert len(raw) <= 33554432
    rom.write_bytes(raw)
    files = list((ROOT / 'experiments/quality_preview').glob('*'))
    report = {'status': 'built_not_tested', 'ROM': str(rom), 'ELF': str(elf),
              'ROM_sha256': hashlib.sha256(raw).hexdigest(), 'ROM_bytes': len(raw),
              'base_v062_ROM_sha256': baseline, 'display': 'GBA Mode 3 RGB555 direct color',
              'scope': 'original opening through first map viewer; not a full gameplay version',
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}}
    out = ROOT / 'evidence/quality_preview';out.mkdir(parents=True, exist_ok=True)
    (out / 'build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
