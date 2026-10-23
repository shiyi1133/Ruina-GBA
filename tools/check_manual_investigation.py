"""Regression for local A versus L/R routing, using genuine ordinary saves.

Only button inputs and read-only observations; no emulator state or RAM writes.
The retained v0.6 binary can reproduce the reported failure with --baseline.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from drive_opening import Emulator, ROOT
from check_save import opening
from save_observation import save_payload


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--baseline', action='store_true')
    args.add_argument('--rom',type=Path)
    args.add_argument('--elf',type=Path)
    options=args.parse_args();baseline=options.baseline
    build = ROOT / ('history/map_action_v061_20261022/build' if baseline else 'build')
    rom = options.rom or build / '废都物语_GBA_开篇开发验证版.gba'
    elf = options.elf or build / 'ruina_opening_dev.elf'
    digest = hashlib.sha256(rom.read_bytes()).hexdigest()
    out = ROOT / 'evidence/manual_investigation' / digest[:12]
    out.mkdir(parents=True, exist_ok=True)
    rows, processes = [], []
    source_save = ROOT / 'evidence/chapter_progress/after_checkpoint_town.sav'

    def state(e):
        return struct.unpack('<4i', e.memory(e.symbols['game'] + 29768, 16))

    def boot(save=source_save):
        e = Emulator(save, rom=rom, elf=elf)
        e.frames(30); e.key(1); e.key(128); e.key(1); e.frames(120)
        assert e.debug()[15] == 4, e.debug()
        return e

    def close(e):
        processes.append(e.log.copy())
        e.close()

    def select(e, point):
        for _ in range(100):
            if state(e)[3] == point:
                return
            e.key(256)
        raise AssertionError(('point not selectable', point, state(e)))

    def walk(e, x, y):
        start_map = state(e)[0]
        for _ in range(50):
            before = state(e)
            assert before[0] == start_map, before
            if before[1:3] == (x, y):
                e.frames(30)
                return
            key = 16 if before[1] < x else 32 if before[1] > x else 128 if before[2] < y else 64
            for _ in range(160):
                e.frames(1, key)
                if state(e)[1:3] != before[1:3]:
                    break
            else:
                raise AssertionError(('blocked manual walk', before, (x, y)))
            e.frames(30)
        raise AssertionError(('manual walk limit', state(e), (x, y)))

    def reaches(e, target_map):
        for _ in range(200):
            assert e.debug()[0] != 0x4641554c and e.debug()[15] != 5, e.debug()
            if state(e)[0] == target_map:
                e.frames(30)
                return True
            if e.debug()[15] in (1, 2, 6, 7, 12):
                return False
            e.frames(6)
        return False

    try:
        e = boot()
        try:
            assert state(e)[:3] == (3, 9, 1), state(e)
            select(e, 2)  # Cave entrance; the tavern is event 1 at (9,4).
            e.shot(out / '01_remote_cave_selected.png')
            walk(e, 9, 4)
            before = state(e)
            e.shot(out / '02_manually_at_tavern.png')
            e.key(1)
            correct = reaches(e, 4)
            e.shot(out / '03_A_result.png')
            rows.append({'check': 'manual A enters the tavern under the cursor instead of the old cave target',
                         'before': before, 'after': state(e), 'ui': e.debug()[15], 'pass': correct})
            if baseline:
                assert not correct and before[3] == 2, rows[-1]
            else:
                assert correct and before[3] == 0, rows[-1]
        finally:
            close(e)

        if not baseline:
            e = boot()
            try:
                select(e, 2); walk(e, 9, 2)
                before = state(e)
                assert before[3] == 0, before
                e.key(1); e.frames(120)
                assert state(e) == before and e.debug()[15] == 4, (before, state(e), e.debug())
                assert not any(struct.unpack('<2I', e.memory(e.symbols['world_trace'] + 16, 8)))
                e.key(8); e.key(2); e.frames(60)
                assert state(e) == before and e.debug()[15] == 4, (state(e), e.debug())
                e.key(1); e.frames(120)
                assert state(e) == before and e.debug()[15] == 4, (state(e), e.debug())
                e.shot(out / '04_empty_tile_after_menu.png')
                rows.append({'check': 'A on an empty tile stays local before and after closing the menu', 'pass': True})
                select(e, 1); e.key(1)
                assert reaches(e, 4), (state(e), e.debug())
                rows.append({'check': 'L/R selection re-enables automatic walking and investigation', 'pass': True})
            finally:
                close(e)

            e = boot()
            try:
                select(e, 2)
                before = state(e)
                e.key(256 | 16); e.frames(30)
                assert state(e) == before, (before, state(e))
                rows.append({'check': 'R plus direction only pans the camera and preserves the chosen point', 'pass': True})
                walk(e, 9, 4)
                assert state(e)[3] == 0, state(e)
                e.key(8); e.key(128); e.key(128); e.key(1)
                assert e.debug()[15] == 1, e.debug()
                saved = out / 'manual_tavern.sav'
                assert e.command('savecopy ' + str(saved)).startswith('SAVE ')
                version, payload = save_payload(saved.read_bytes())
                assert version == 5 and struct.unpack_from('<4i', payload, 29768) == (3, 9, 4, 0)
            finally:
                close(e)
            e = boot(saved)
            try:
                assert state(e) == (3, 9, 4, 0), state(e)
                e.shot(out / '05_manual_position_cold_loaded.png')
                e.key(1)
                assert reaches(e, 4), (state(e), e.debug())
                rows.append({'check': 'ordinary SAV cold load preserves local mode and A enters the local tavern', 'pass': True})
            finally:
                close(e)

            e = Emulator(rom=rom, elf=elf)
            try:
                opening(e, 1); e.frames(30)
                assert state(e)[0] == 23 and state(e)[3] == 1, state(e)
                rows.append({'check': 'new-game map still initially highlights its available entrance', 'pass': True})
            finally:
                close(e)

        report = {'status': 'reported_bug_reproduced' if baseline else 'pass', 'rom_sha256': digest,
                  'checks': rows, 'commands': processes, 'input': 'real emulated buttons; genuine ordinary SAV',
                  'memory': 'read only', 'instant_states': False, 'hardware': 'not_run'}
        (out / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        if not baseline:
            (out.parent / 'latest_attempt.json').write_text(json.dumps({'status': 'pass', 'report': str((out / 'result.json').relative_to(ROOT))}, ensure_ascii=False, indent=2))
        print(json.dumps({k: v for k, v in report.items() if k != 'commands'}, ensure_ascii=False, indent=2))
    except Exception as error:
        (out / 'failure.json').write_text(json.dumps({'status': 'fail', 'error': repr(error), 'checks': rows, 'commands': processes}, ensure_ascii=False, indent=2))
        raise


if __name__ == '__main__':
    main()
