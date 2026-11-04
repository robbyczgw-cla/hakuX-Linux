#!/usr/bin/env python3
"""Run positive/negative platform checks and generate copyright-free XISO fixtures."""
import argparse
import os
from pathlib import Path
import struct
import subprocess
import tempfile


def disc(path, code, imports=()):
    """A disc whose default.xbe runs code at 0x11000 (its section takes whole
    pages), with the kernel's ordinals in imports through the thunks at 0x10f00."""
    size = max(0x1000, -(-len(code) // 0x1000) * 0x1000)
    xbe = bytearray(max(0x1010, 0x1000 + len(code)))
    def word(offset, value):
        struct.pack_into('<I', xbe, offset, value)
    for offset, value in {
        0: 0x48454258, 0x104: 0x10000, 0x108: 0x1000, 0x10c: 0x1000 + size,
        0x118: 0x10200, 0x11c: 1, 0x120: 0x10400,
        0x128: 0x11000 ^ 0xa8fc57ab, 0x130: 0x1000,
        0x158: 0x10f00 ^ 0x5b6d40b6, 0x164: 0x10a00, 0x208: 0xffff0001,
        0x400: 6, 0x404: 0x11000, 0x408: size,
        0x40c: 0x1000, 0x410: len(code), 0x414: 0x10800,
    }.items():
        word(offset, value)
    for i, ordinal in enumerate(imports):
        word(0xf00 + 4 * i, 0x80000000 | ordinal)
    xbe[0x800:0x806] = b'.text\0'
    xbe[0x1000:0x1000 + len(code)] = code
    image = bytearray(34 * 2048) + xbe
    magic = b'MICROSOFT*XBOX*MEDIA'
    image[32 * 2048:32 * 2048 + 20] = magic
    image[32 * 2048 + 0x7ec:33 * 2048] = magic
    struct.pack_into('<II', image, 32 * 2048 + 20, 33, 32)
    name = b'default.xbe'
    struct.pack_into('<HHIIBB', image, 33 * 2048, 0, 0, 34, len(xbe), 0, len(name))
    image[33 * 2048 + 14:33 * 2048 + 14 + len(name)] = name
    path.write_bytes(image)


def named_objects_code():
    """A guest that names an event (XAPI's CreateEvent: relative to
    ObWin32NamedObjectsDirectory, -4, with OBJ_OPENIF), creates it again, opens
    it by name in another case (OpenEvent: ObOpenObjectByName) and by its
    absolute name, signals it through the opened handle, and checks the
    errors: a wrong type, a missing name, and the name gone once every handle
    is closed. HLT when all hold; a failed check N stores to address 0 at
    its own eip (f<N>)."""
    T = {'create': 0x10f00, 'open': 0x10f04, 'close': 0x10f08, 'evtype': 0x10f0c, 'semtype': 0x10f10,
         'set': 0x10f14, 'wait': 0x10f18}
    D = 0x11800
    H1, H2, H3, H4, ZERO = D, D + 4, D + 8, D + 12, D + 16
    names = {'create': (D + 0x20, D + 0x60, D + 0x100, b'TestEvent', 0x80),
             'open': (D + 0x30, D + 0x68, D + 0x110, b'tESTeVENT', 0),
             'missing': (D + 0x40, D + 0x70, D + 0x120, b'Missing', 0),
             'abs': (D + 0x50, D + 0x78, D + 0x130, b'\\BaseNamedObjects\\TestEvent', 0)}
    code = bytearray()
    fails = []
    def emit(*parts):
        for p in parts:
            code.extend(p)
    def u32(v):
        return struct.pack('<I', v & 0xffffffff)
    def store(addr, value):                 # mov dword [addr], value
        emit(b'\xc7\x05', u32(addr), u32(value))
    def push(v):
        emit(b'\x68', u32(v))
    def push_mem(addr):
        emit(b'\xff\x35', u32(addr))
    def call(name):
        emit(b'\xff\x15', u32(T[name]))
    def expect(status):                     # cmp eax, status; jne f<N>
        emit(b'\x3d', u32(status), b'\x0f\x85')
        fails.append(len(code))
        emit(u32(0))
    root = {'abs': 0}
    for key, (oa, string, chars, text, attributes) in names.items():
        store(string, len(text) | len(text) << 16)
        store(string + 4, chars)
        store(oa, root.get(key, 0xfffffffc))
        store(oa + 4, string)
        store(oa + 8, attributes)
    def open_(key, type_slot, handle=H4):
        push(handle), push(0)
        push_mem(T[type_slot]) if type_slot else push(0)
        push(names[key][0]), call('open')
    push(0), push(0), push(names['create'][0]), push(H1), call('create'), expect(0)
    push(0), push(0), push(names['create'][0]), push(H3), call('create'), expect(0x40000000)
    open_('open', 'evtype', H2), expect(0)
    push(0), push_mem(H2), call('set')
    push(ZERO), push(0), push_mem(H1), call('wait'), expect(0)
    open_('open', 'semtype'), expect(0xc0000024)
    open_('missing', 'evtype'), expect(0xc0000034)
    open_('abs', None), expect(0)
    push_mem(H4), call('close')
    for h in (H1, H2, H3):
        push_mem(h), call('close')
    open_('open', 'evtype'), expect(0xc0000034)
    emit(b'\xf4')
    for n, at in enumerate(fails, 1):       # f<N>: mov dword [0], N
        struct.pack_into('<i', code, at, len(code) - (at + 4))
        store(0, n)
    code.extend(bytes(0x900 - len(code)))
    for oa, string, chars, text, attributes in names.values():
        code.extend(bytes(chars - 0x11000 - len(code)))
        code.extend(text)
    return bytes(code)


def run(command, expected, marker, env=None):
    result = subprocess.run([str(x) for x in command], env=env, capture_output=True, text=True, timeout=15)
    print(result.stdout, end='')
    print(result.stderr, end='')
    markers = (marker,) if isinstance(marker, str) else marker
    if result.returncode != expected or any(m not in result.stdout + result.stderr for m in markers):
        raise SystemExit(f'FAIL: {command}: expected exit {expected} with {markers!r}, got {result.returncode}')
    print(f'PASS: {Path(command[0]).name} {list(map(str, command[1:]))}: expected exit {expected}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--fixtures', type=Path, help='Only generate fixtures for transfer to a device without Python')
    args = parser.parse_args()
    if args.fixtures:
        args.fixtures.mkdir(parents=True, exist_ok=True)
        disc(args.fixtures / 'halt.iso', b'\xf4')
        disc(args.fixtures / 'spin.iso', b'\xeb\xfe')
        return
    build = args.build.resolve()
    run([build / 'linux-smoke'], 0, 'translated MMIO')
    run([build / 'linux-smoke', '--wrong-expectation'], 1, 'FAIL: translated arithmetic')
    run([build / 'linux-smoke', '--host-fault'], 3, 'FAIL: unexpected host fault')
    run([build / 'audio-smoke'], 0, 'audio resumes')
    with tempfile.TemporaryDirectory(prefix='hakux-day1-') as folder:
        root = Path(folder)
        env = dict(os.environ, NC_TIMEOUT='1')
        run([build / 'xboxrun', '--headless', root / 'missing.iso', root / 'data'], 2, 'No such file', env)
        (root / 'invalid.iso').write_bytes(b'not an Xbox disc')
        run([build / 'xboxrun', '--headless', root / 'invalid.iso', root / 'data'], 1, 'boot failed', env)
        disc(root / 'halt.iso', b'\xf4')
        disc(root / 'spin.iso', b'\xeb\xfe')
        run([build / 'xboxrun', '--headless', root / 'halt.iso', root / 'data'], 0, 'guest executed HLT', env)
        run([build / 'xboxrun', '--headless', root / 'halt.iso', root / 'data', 'lang=2', 'net=off'], 0,
            ('console language 2', 'guest executed HLT'), env)
        run([build / 'xboxrun', '--headless', root / 'halt.iso', root / 'data', 'unknown=1'], 2,
            'unknown option unknown=1', env)
        # The renderer's boot path (drawing itself needs a title and a GPU).
        run([build / 'xboxrun', '--render', root / 'halt.iso', root / 'render'], 0,
            ('renderer ON without a display', 'guest executed HLT'), env)
        # Named objects: XAPI's CreateEvent and OpenEvent through the kernel.
        disc(root / 'named.iso', named_objects_code(), (189, 243, 187, 16, 30, 225, 233))
        run([build / 'xboxrun', '--headless', root / 'named.iso', root / 'named'], 0, 'guest executed HLT', env)
        run([build / 'xboxrun', '--headless', root / 'spin.iso', root / 'data'], 5, 'timeout after 1 s', env)


if __name__ == '__main__':
    main()
