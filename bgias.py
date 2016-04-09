#!/usr/bin/env python3
"""
BGI script file assembler
"""

import glob
import os
import struct
import sys
import polib

import buriko_common
import bgi_po
import buriko_setup

import asdis
import bgiop


def parse_instr(line, linenum, inputpo):
    """
    Parse a line from a .bsd file and transform it into structured data
    using given .po resources
    Returns: tuple (str, array, set)
    """
    strings = set([])
    fcn, argstr = asdis.re_instr.match(line).groups()
    argstr = argstr.strip()
    if argstr:
        argstr = argstr.replace('\\\\', asdis.backslash_replace).replace('\\"', asdis.quote_replace)
        quotes = asdis.get_quotes(argstr)
        if len(quotes) % 2 != 0:
            raise asdis.QuoteMismatch('Mismatched quotes @ line %d' % linenum)
        argstr = asdis.replace_quote_commas(argstr, quotes)
        args = [
            x
            .strip()
            .replace(asdis.comma_replace, ',')
            .replace(asdis.quote_replace, '\\"')
            .replace(asdis.backslash_replace, '\\\\')
            for x in argstr.split(',')
        ]
        string_to_add = None
        for arg in args:
            if arg and arg[0] == '"' and arg[-1] == '"':
                string_to_add = arg
        if fcn == 'push_string':
            if args[0].startswith('MSGID::'):
                msgid = args[0][7:]
                ent = inputpo.find_by_prefix("{}:".format(msgid))
                if (
                        ent is not None and
                        ent.msgstr != "" and
                        not ent.msgstr.startswith("NAME:")
                ):
                    args[1] = '"{}"'.format(ent.msgstr)
                del args[0]
                string_to_add = args[0]
        if string_to_add is not None:
            strings.add(string_to_add)
    else:
        args = []
    return fcn, args, strings


def parse(asmtxt, inputpo):
    """
    Parse the .bsd disassembly into structured data using given .po resources
    Returns: tuple(array of lists, dict, array of str, bytes, dict)
    - instrs: list is (fcn:str, args:array, pos:integer, index:integer)
    - symbols: dict { str: integer } for labels and resources
    - texts: strings in text section
    - hdrtext: header identifier
    - defines: metadata defined in bsd header
    """
    instrs = []
    symbols = {}
    text_set = set()
    pos = 0
    hdrtext = None
    defines = {}
    for lineidx, line in enumerate(asmtxt.split('\n')):
        line = line.strip()
        line = asdis.remove_comment(line)
        if not line:
            continue
        if asdis.re_header.match(line):
            hdrtext, = asdis.re_header.match(line).groups()
            hdrtext = asdis.unescape(hdrtext)
        elif asdis.re_define.match(line):
            name, offset_s = asdis.re_define.match(line).groups()
            defines[name] = offset_s
        elif asdis.re_label.match(line):
            symbol, = asdis.re_label.match(line).groups()
            symbols[symbol] = pos
        elif asdis.re_instr.match(line):
            fcn, args, strings = parse_instr(line, lineidx + 1, inputpo)
            record = fcn, args, pos, lineidx + 1
            text_set.update(strings)
            instrs.append(record)
            try:
                opcode = bgiop.rops[fcn]
            except KeyError:
                raise asdis.InvalidFunction('Invalid function @ line %d' % (lineidx + 1))
            pos += struct.calcsize(bgiop.ops[opcode][0]) + 4
        else:
            raise asdis.InvalidInstructionFormat(
                'Invalid instruction format @ line {:d}'.format(lineidx + 1))
    texts = []
    for text in text_set:
        symbols[text] = pos
        text = asdis.unescape(text[1:-1])
        texts.append(text)
        pos += len(text.encode(buriko_setup.ienc)) + 1
    return instrs, symbols, texts, hdrtext, defines


def out_hdr(asmoutfile, hdrtext, defines, symbols):
    """
    Write the BGI script header to a binary file buffer `asmoutfile`
    Its length is 0x1C bytes + alpha
    """
    asmoutfile.write(hdrtext.encode(buriko_setup.ienc).ljust(0x1C, b'\x00'))
    entries = len(defines)
    hdrsize = 12 + 4 * entries
    hdrsize += sum(len(name.encode(buriko_setup.ienc)) + 1 for name in defines)
    padding = ((hdrsize + 11) >> 4 << 4) + 4 - hdrsize
    hdrsize += padding
    asmoutfile.write(struct.pack('<III', hdrsize, 0, entries))
    for name in sorted(defines, key=lambda x: symbols[x]):
        asmoutfile.write(name.encode(buriko_setup.ienc) + b'\x00')
        asmoutfile.write(struct.pack('<I', symbols[name]))
    asmoutfile.write(b'\x00' * padding)


def out(asmoutfile, instrs, symbols, texts, hdrtext, defines):
    """
    Write to a binary file buffer `asmoutfile` using data gathered from parse()
    """
    if hdrtext:
        out_hdr(asmoutfile, hdrtext, defines, symbols)
    for fcn, args, _, _ in instrs:
        opcode = bgiop.rops[fcn]
        asmoutfile.write(struct.pack('<I', opcode))
        for arg in args:
            if arg in symbols:
                asmoutfile.write(struct.pack('<I', symbols[arg]))
            elif arg.startswith('0x') or arg.startswith('-0x'):
                asmoutfile.write(struct.pack('<i', int(arg, 16)))
            elif arg:
                asmoutfile.write(struct.pack('<i', int(arg)))
    for text in texts:
        asmoutfile.write(text.encode(buriko_setup.ienc) + b'\x00')


def asm(asmpath):
    """
    Assemble a BGI script file from .bsd and .po resources
    """
    buriko_common.makedir('{}/compiled'.format(buriko_setup.project_name))
    scriptname = os.path.splitext(os.path.basename(asmpath))[0]
    ofilepath = '{}/compiled/{}'.format(buriko_setup.project_name, scriptname)
    in_popath = "{}/{}/{}.po".format(buriko_setup.project_name, scriptname, buriko_setup.ilang)
    in_po = polib.pofile(in_popath, klass=bgi_po.IndexedPo)
    asmtxt = open(asmpath, 'r', encoding='utf-8-sig').read()

    instrs, symbols, texts, hdrtext, defines = parse(asmtxt, in_po)

    with open(ofilepath, 'wb') as asmfile:
        out(asmfile, instrs, symbols, texts, hdrtext, defines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: bgias.py <file(s)>')
        print('(only .bsd files amongst <file(s)> will be processed)')
        sys.exit(1)
    for sysarg in sys.argv[1:]:
        for script in glob.glob(sysarg):
            base, ext = os.path.splitext(script)
            if ext == '.bsd':
                # print('Assembling %s...' % script)
                asm(script)
            else:
                print('skipping: {} (not .bsd)'.format(script), file=sys.stderr)
