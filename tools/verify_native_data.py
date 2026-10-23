"""Check the allocation-free native reader against original data, on the host.

This verifies ROM-data access. It does not execute game rules or a GBA emulator.
"""
import ctypes as C
import json
import subprocess
from pathlib import Path
from inspect_lcf import ROOT, Reader, array, commands, data_root, fields


class Span(C.Structure):
    _fields_ = [('data', C.POINTER(C.c_ubyte)), ('size', C.c_uint)]


class Cursor(C.Structure):
    _fields_ = [('span', Span), ('pos', C.c_uint), ('error', C.c_int)]


class Command(C.Structure):
    _fields_ = [('code', C.c_uint), ('indent', C.c_uint),
                ('parameter_count', C.c_uint), ('text', Span), ('parameters', Span)]


def raw(s):
    return C.string_at(s.data, s.size) if s.size else b''


def span(b):
    owner = (C.c_ubyte * len(b)).from_buffer_copy(b)
    return Span(owner, len(b)), owner


def main():
    target = ROOT / 'build' / 'lcf_host.so'
    subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-fPIC', '-shared', str(ROOT/'runtime/rm2k/lcf.c'), '-o', str(target)], check=True)
    lib = C.CDLL(str(target))
    lib.lcf_field.argtypes = [Span, C.c_uint, C.POINTER(Span)]
    lib.lcf_array.argtypes = [Span, C.c_uint, C.POINTER(Span)]
    lib.lcf_command.argtypes = [C.POINTER(Cursor), C.POINTER(Command)]
    lib.lcf_command_values.argtypes = [C.POINTER(Cursor), C.POINTER(Command), C.POINTER(C.c_int), C.c_uint]
    lib.lcf_resource.argtypes = [Span, C.c_char_p, C.POINTER(Span)]
    pack = (ROOT/'build/original_lcf.bin').read_bytes()
    packed, packed_owner = span(pack)
    counts = {'files': 0, 'fields': 0, 'array_entries': 0, 'commands': 0,
              'invalid_inputs_rejected': 0, 'single_pass_commands': 0}

    def check_fields(data):
        native, owner = span(data)
        expected = fields(data)
        for key, value in expected.items():
            got = Span()
            assert lib.lcf_field(native, key, C.byref(got)) == 1
            assert raw(got) == value
            counts['fields'] += 1
        absent = Span()
        assert lib.lcf_field(native, 0x10000, C.byref(absent)) == 0
        return expected

    def check_array(data):
        native, owner = span(data)
        result = array(data)
        for key, value in result:
            got = Span()
            assert lib.lcf_array(native, key, C.byref(got)) == 1
            assert check_fields(raw(got)) == value
            counts['array_entries'] += 1
        return result

    def check_commands(data):
        native, owner = span(data)
        cursor = Cursor(native, 0, 0)
        single = Cursor(native, 0, 0)
        expected = commands(data)
        for want in expected:
            got = Command()
            assert lib.lcf_command(C.byref(cursor), C.byref(got)) == 1
            assert (got.code, got.indent, got.parameter_count) == (
                want['code'], want['indent'], len(want['params']))
            assert raw(got.text).decode('gbk', errors='replace') == want['text']
            p = Reader(raw(got.parameters))
            values = [p.num() for _ in range(got.parameter_count)]
            values = [n - 0x100000000 if n >= 0x80000000 else n for n in values]
            assert values == want['params']
            decoded = (C.c_int * max(1, len(values)))()
            once = Command()
            assert lib.lcf_command_values(C.byref(single), C.byref(once), decoded, len(values)) == 1
            assert single.pos == cursor.pos
            assert (once.code, once.indent, once.parameter_count) == (got.code, got.indent, got.parameter_count)
            assert raw(once.text) == raw(got.text) and raw(once.parameters) == raw(got.parameters)
            assert list(decoded)[:len(values)] == values
            counts['single_pass_commands'] += 1
            counts['commands'] += 1
        assert cursor.pos == len(data) and not cursor.error

    for file in sorted((ROOT/'build/original').iterdir()):
        if file.suffix not in ('.lmu', '.ldb', '.lmt'):
            continue
        original = file.read_bytes()
        got = Span()
        assert lib.lcf_resource(packed, file.name.encode(), C.byref(got)) == 1
        assert raw(got) == original
        counts['files'] += 1
        header, root = data_root(original)
        if file.suffix == '.lmt':
            # Map tree format has trailing engine-specific data; preserve verbatim.
            continue
        reader = Reader(original)
        reader.string()
        check_fields(original[reader.at:])
        if file.suffix == '.ldb':
            for table in range(11, 26):
                if table == 21 or table == 22 or table not in root:
                    continue
                for key, value in check_array(root[table]):
                    if table == 25:
                        check_commands(value.get(22, b''))
                    if table == 15:
                        for _, page in check_array(value.get(11, b'\0')):
                            check_commands(page.get(12, b''))
        elif file.suffix == '.lmu':
            for _, event in check_array(root.get(81, b'\0')):
                for _, page in check_array(event.get(5, b'\0')):
                    check_commands(page.get(52, b''))
    for data in (b'\x80', b'\xff\xff\xff\xff\xff\xff',
                 b'\x81\x80\x80\x80\x80\x00'):
        native, owner = span(data)
        cursor = Cursor(native, 0, 0)
        value = C.c_uint()
        assert lib.lcf_number(C.byref(cursor), C.byref(value)) == 0
        assert cursor.error
        counts['invalid_inputs_rejected'] += 1
    report = {'test': 'native LCF reader versus unchanged original data',
              'host': 'Linux host, not GBA emulation', 'status': 'pass', **counts,
              'game_rule_execution': 'not_run', 'chapter_playthrough': 'not_run'}
    (ROOT/'evidence/native_reader_checks.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
