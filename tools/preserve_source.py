"""Freeze original LCF data without applying balance or event transformations.

The native runtime must read these bytes with RPG Maker 2000 semantics. This is
an integrity/data-transport check, not proof that a runtime implements the rules.
Missing fields stay missing; liblcf defaults may not be replaced with zeroes.
"""
from pathlib import Path
import hashlib
import json
import struct
import zipfile

from inspect_lcf import ROOT, ZIP, Reader, array, commands, data_root, fields, integer, text


def sha(data):
    return hashlib.sha256(data).hexdigest()


def number(n):
    """LCF signed int32 values are represented as unsigned BE base-128 VLQs."""
    n &= 0xFFFFFFFF
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7F))
        n >>= 7
    return bytes(reversed(out))


def command_roundtrip(blob):
    """Prove text bytes, parameters, indentation and end markers are untouched."""
    r = Reader(blob)
    encoded = bytearray()
    count = 0
    invalid_gbk = []
    while r.at < len(blob):
        code, indent = r.num(), r.num()
        s = r.string()
        n = r.num()
        params = [r.num() for _ in range(n)]
        encoded += number(code) + number(indent) + number(len(s)) + s + number(n)
        for p in params:
            encoded += number(p)
        # Only text-facing commands use GBK. File names and comments can be JP.
        if code in (10110, 20110, 10140, 20140, 10610, 10620):
            try:
                s.decode('gbk', errors='strict')
            except UnicodeDecodeError:
                invalid_gbk.append(count)
        count += 1
    assert bytes(encoded) == blob, 'LCF command stream changed during transport'
    return count, invalid_gbk


def main():
    contract = json.loads((ROOT / '移植约定.json').read_text())
    archive_hash = sha(ZIP.read_bytes())
    assert archive_hash == contract['source_sha256'], 'Original archive changed'
    out = ROOT / 'build' / 'original'
    out.mkdir(parents=True, exist_ok=True)
    report = {
        'source_sha256': archive_hash,
        'data_integrity': 'pass',
        'runtime_rules': 'not_run',
        'gba_playthrough': 'not_run',
        'gba_ordinary_save_cold_load': 'not_run',
        'hardware': 'not_run',
        'files': [],
        'command_count': 0,
        'text_decoding_requires_review': [],
    }
    resources = []
    with zipfile.ZipFile(ZIP) as z:
        members = sorted(i for i in z.namelist()
                         if i.startswith('Ruina121/game/')
                         and Path(i).suffix.lower() in ('.ldb', '.lmt', '.lmu'))
        for member in members:
            raw = z.read(member)
            name = Path(member).name
            (out / name).write_bytes(raw)
            assert (out / name).read_bytes() == raw
            resources.append((name, raw))
            report['files'].append({'name': name, 'bytes': len(raw), 'sha256': sha(raw)})
            header, root = data_root(raw)
            streams = []
            if name.endswith('.lmu'):
                for eid, event in array(root.get(81, b'')):
                    for pid, page in array(event.get(5, b'')):
                        streams.append((f'{name}/event{eid}/page{pid}', page.get(52, b'')))
            elif name.endswith('.ldb'):
                for cid, common in array(root.get(25, b'')):
                    streams.append((f'common/{cid}', common.get(22, b'')))
                for tid, troop in array(root.get(15, b'')):
                    for pid, page in array(troop.get(11, b'')):
                        streams.append((f'troop/{tid}/page{pid}', page.get(12, b'')))
            for location, stream in streams:
                n, invalid = command_roundtrip(stream)
                report['command_count'] += n
                if invalid:
                    report['text_decoding_requires_review'].append(
                        {'source': location, 'commands': invalid})
        db = data_root(z.read('Ruina121/game/RPG_RT.ldb'))[1]
        actors = dict(array(db[11]))
        enemies = dict(array(db[14]))
        items = dict(array(db[13]))
        troops = dict(array(db[15]))
        snapshot = {'actors': [], 'enemies': [], 'troops': [], 'initial_items': []}
        for aid in range(1, 15):
            a = actors[aid]
            p = a[31]
            levels = len(p) // 12
            stats = [struct.unpack_from('<H', p, i * levels * 2)[0] for i in range(6)]
            snapshot['actors'].append({
                'id': aid, 'name': text(a[1]),
                'level1_hp_mp_attack_defense_spirit_agility': stats,
                'equipment': list(struct.unpack('<5H', a[51])),
                'skills': [{'level': integer(v.get(1, b''), 1),
                            'skill': integer(v.get(2, b''), 1)}
                           for _, v in array(a.get(63, b''))],
                'raw_fields': {str(k): v.hex() for k, v in a.items()},
            })
        for eid in (1, 2, 7):
            e = enemies[eid]
            snapshot['enemies'].append({
                'id': eid, 'name': text(e[1]),
                'explicit_fields': {str(k): v.hex() for k, v in e.items()},
                'ai_actions': [{str(k): v.hex() for k, v in action.items()}
                               for _, action in array(e.get(42, b''))],
            })
        for tid in (1, 6, 13):
            t = troops[tid]
            members = array(t.get(2, b''))
            snapshot['troops'].append({
                'id': tid, 'name': text(t[1]),
                'members': [{str(k): v.hex() for k, v in m.items()}
                            for _, m in members],
                'visible_member_count': sum(not integer(m.get(4, b'')) for _, m in members),
                'hidden_members': [{'index': index, 'enemy_id': integer(m.get(1, b''), 1)}
                                   for index, m in members if integer(m.get(4, b''))],
            })
        # Directly observed in Map0002 original initialisation commands.
        for iid, count in ((10, 1), (14, 3), (20, 1), (58, 3), (22, 1)):
            snapshot['initial_items'].append({'id': iid, 'name': text(items[iid][1]), 'count': count})
        assert snapshot['actors'][0]['level1_hp_mp_attack_defense_spirit_agility'] == [36, 7, 11, 9, 8, 16]
        assert snapshot['troops'][1]['visible_member_count'] == 5
        assert len(snapshot['troops'][1]['members']) == 7
        (ROOT / 'research' / 'opening_baseline.json').write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2))
    # Indexed blob can be linked into GBA ROM; payload is the exact original LCF.
    # Fixed-size entries avoid decompressing the database into scarce GBA RAM.
    index_size = 12 + len(resources) * 48
    index = bytearray(b'RLCFORIG' + struct.pack('<I', len(resources)))
    body = bytearray()
    for name, raw in resources:
        pad = (-len(body)) % 4
        body += bytes(pad)
        index += name.encode('ascii').ljust(32, b'\0')
        index += struct.pack('<IIII', index_size + len(body), len(raw), 0, 0)
        body += raw
    blob = bytes(index + body)
    (ROOT / 'build' / 'original_lcf.bin').write_bytes(blob)
    # Re-read the actual emitted transport, not just the source objects.
    for i, (name, raw) in enumerate(resources):
        entry = 12 + i * 48
        offset, size = struct.unpack_from('<II', blob, entry + 32)
        assert blob[offset:offset + size] == raw, name
    report['rom_data_blob'] = {'bytes': len(blob), 'sha256': sha(blob),
                               'byte_for_byte_source_comparison': 'pass'}
    (ROOT / 'evidence' / 'original_data_integrity.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ('files', 'text_decoding_requires_review')},
                     ensure_ascii=False, indent=2))
    print('Text encoding review locations:', len(report['text_decoding_requires_review']))


if __name__ == '__main__':
    main()
