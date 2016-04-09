#!/usr/bin/env python3
"""
BGI script file disassembler
"""
import glob
import os
import struct
import sys

import buriko_common
import buriko_setup

import asdis
import bgiop


def parse_hdr(hdr):
    """
    Parse the BGI script header which is 0x1C bytes + alpha
    Returns: tuple(bytes, dict)
    """
    hdrtext = hdr[:0x1C].rstrip(b'\x00').decode(buriko_setup.senc)
    defines = {}
    entries, = struct.unpack('<I', hdr[0x24:0x28])
    pos = 0x28
    for _ in range(entries):
        pos1 = hdr.find(b'\x00', pos)
        name = hdr[pos:pos1].decode(buriko_setup.senc)
        pos = pos1 + 1
        offset, = struct.unpack('<I', hdr[pos:pos + 4])
        defines[offset] = name
        pos += 4
    return hdrtext, defines


def parse(code, hdr):
    """
    Parse the code section, with an optional header (0-length bytes otherwise)
    Returns: tuple(dict, dict, bytes, dict)
    """
    if hdr:
        hdrtext, defines = parse_hdr(hdr)
    else:
        hdrtext = None
        defines = {}
    bgiop.clear_offsets()
    inst = {}
    size = buriko_common.get_section_boundary(code)
    pos = 0
    idx = 1
    while pos < size:
        addr = pos
        opcode, = struct.unpack('<I', code[addr:addr + 4])
        if opcode not in bgiop.ops:
            raise Exception('size unknown for op %02x @ offset %05x' % (opcode, addr))
        pos += 4
        fmt, pfmt, fcn = bgiop.ops[opcode]
        if fmt:
            oplen = struct.calcsize(fmt)
            args = struct.unpack(fmt, code[pos:pos + oplen])
            if fcn:
                args = fcn(code, addr, defines, *args)
                if fcn == bgiop.get_string:
                    args = list(args)
                    args.append(idx)
                    idx = idx + 1
            inst[addr] = pfmt.format(*args)
            pos += oplen
        else:
            inst[addr] = pfmt
    offsets = bgiop.offsets.copy()
    return inst, offsets, hdrtext, defines


def out(disasmoutfile, inst, offsets, hdrtext, defines):
    """
    Write to a text file buffer `disasmoutfile` using data gathered from parse()
    """
    if hdrtext:
        disasmoutfile.write('#header "%s"\n\n' % asdis.escape(hdrtext))
    if defines:
        for offset in sorted(defines):
            disasmoutfile.write('#define %s L%05x\n' % (defines[offset], offset))
        disasmoutfile.write('\n')
    for addr in sorted(inst):
        if inst[addr].startswith('line('):
            disasmoutfile.write('\n')
        if addr in offsets or addr in defines:
            if addr in defines:
                disasmoutfile.write('\n%s:\n' % defines[addr])
            else:
                disasmoutfile.write('\nL%05x:\n' % addr)
        disasmoutfile.write('\t%s;\n' % inst[addr])


def dis(scriptpath):
    """
    Disassemble a file and write output to a .bsd file
    """
    buriko_common.makedir(buriko_setup.project_name)  # output folder for all files
    scriptname = os.path.basename(scriptpath)
    ofilepath = os.path.join(buriko_setup.project_name, os.path.splitext(scriptname)[0] + '.bsd')

    infile = open(scriptpath, 'rb')
    hdr_test = infile.read(0x20)
    if hdr_test.startswith(b'BurikoCompiledScriptVer1.00\x00'):
        hdrsize = 0x1C + struct.unpack('<I', hdr_test[0x1C:0x20])[0]
    else:
        hdrsize = 0
    infile.seek(0, 0)
    hdr = infile.read(hdrsize)
    code = infile.read()
    infile.close()

    inst, offsets, hdrtext, defines = parse(code, hdr)

    with open(ofilepath, 'w', encoding='utf-8-sig') as disasmfile:
        out(disasmfile, inst, offsets, hdrtext, defines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: bgidis.py <file(s)>')
        print('(only extension-less files amongst <file(s)> will be processed)')
        sys.exit(1)
    for arg in sys.argv[1:]:
        for script in glob.glob(arg):
            base, ext = os.path.splitext(script)
            if not ext and os.path.isfile(script):
                # print('Disassembling %s...' % script)
                dis(script)
