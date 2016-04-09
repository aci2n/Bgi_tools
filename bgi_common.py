"""
Common routines for handling BGI scripts
"""

import struct
import os
import sys
import errno

import bgi_config
import bgi_setup


class BgiCustomException(Exception):
    """
    Exception type encloses a string describing a generic error occuring
    while processing a BGI script.
    """
    pass


def makedir(dirname):
    """
    Tries to make a directory recursively, and fails silently a component already exists.
    Other exceptions are raised normally.
    Returns: None
    """
    try:
        os.makedirs(dirname)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            raise


def escape(text):
    """
    Escapes text when writing to a resource file.
    Returns: str
    """
    text = text.replace('\n', '\\n')
    return text


def unescape(text):
    """
    Unescapes text when reading to a resource file.
    Returns: str
    """
    text = text.replace('\\n', '\n')
    return text


def get_byte(data, offset):
    """
    Helper function to read 1 byte from a bytes buffer
    Returns: integer
    """
    data = data[offset:offset + 1]
    if len(data) < 1:
        return None
    return struct.unpack('B', data)[0]


def get_word(data, offset):
    """
    Helper function to read 2 bytes from a bytes buffer
    Returns: integer
    """
    data = data[offset:offset + 2]
    if len(data) < 2:
        return None
    return struct.unpack('<H', data)[0]


def get_dword(data, offset):
    """
    Helper function to read 4 bytes from a bytes buffer
    Returns: integer
    """
    data = data[offset:offset + 4]
    if len(data) < 4:
        return None
    return struct.unpack('<I', data)[0]


def get_section_boundary(data):
    """
    Scans a BGI script buffer for the boundary before the text section
    ---
    This is somewhat of a kludge to get the beginning of the text section as it assumes
    that the code section ends with the byte sequence: 1B 00 00 00
    (this is probably a return or exit command).
    Returns: integer offset of boundary, or -1
    """
    pos = -1
    while 1:
        res = data.find(b'\x1B\x00\x00\x00', pos + 1)
        if res == -1:
            break
        pos = res
    return pos + 4


def split_data(data):
    """
    Split a BGI script buffer into its components
    Returns: (bytes, bytes, bytes, dict: info on detected script version)
    """
    config = bgi_config.get_config(data)
    section_boundary = get_section_boundary(data)
    hdr_size = config['HDR_SIZE']
    if config['HDRAS_POS'] is not None:
        hdr_size += get_dword(data, config['HDRAS_POS'])
    hdr_bytes = data[:hdr_size]
    code_bytes = data[hdr_size:section_boundary]
    text_bytes = data[section_boundary:]
    return hdr_bytes, code_bytes, text_bytes, config


def get_text_section(text_bytes, decode_binstrings=True):
    """
    Parses a BGI text buffer into a dictionary whose keys are offsets.
    `decode_binstrings` decides whether to decode them to str or
    leave them as a bytes object
    Returns: a dict {offset: str} or {offset: bytes}
    """
    if len(text_bytes) == 0 or text_bytes == b'\x00':
        return {}
    binstrings = text_bytes.rstrip(b'\x00').split(b'\x00')
    text_section = {}
    pos = 0
    for binstring in binstrings:
        raw_length = len(binstring) + 1
        try:
            text = binstring.decode(bgi_setup.senc) if decode_binstrings else binstring
        except UnicodeDecodeError as exc:
            with open('DEBUG.bin', 'wb') as out:
                out.write(binstring)
            raise BgiCustomException(
                "ERROR decoding text @{0:04X} to @{1:04X} - {2}: {3}".format(
                    pos, pos + raw_length, sys.exc_info()[0], exc
                )
            )
        text_section[pos] = text
        pos += raw_length

    return text_section


def check(code_bytes, pos, cfcn, cpos):
    """
    Various checks on bytecode
    Returns: Boolean
    """
    return (cfcn is not None and
            cfcn == get_dword(code_bytes, pos + cpos))


def get_code_section(code_bytes, text_bytes, config):
    """
    Parses the BGI code buffer and associates offsets to misc info.
    Also detects orphaned strings (unused strings in `text_bytes`)
    Returns: tuple (dict {offset: RECORD}, dict {offset: bytes})
    """
    text_section = get_text_section(text_bytes, False)
#    print("{} strings ({} bytes)".format(len(text_section), len(text_bytes)), file=sys.stderr)
#    for addr in sorted(text_section):
#        print("X00:{:04X}".format(addr), file=sys.stderr)
    matched_pos = {}

    pos = 4
    code_size = len(code_bytes)
    code_section = {}
    ids = {'N': 1, 'T': 1, 'Z': 1}
    names = {}
    others = {}
    while pos < code_size:
        optype = get_dword(code_bytes, pos - 4)
        dword = get_dword(code_bytes, pos)
        text_addr = dword - code_size
        # check if address is in text section and data type is string or file
        if text_addr in text_section:
            matched_pos[text_addr] = True
#            print("REF:{:04X}".format(text_addr))
            text = text_section[text_addr]
            if optype == config['STR_TYPE']:
                text = text.decode(bgi_setup.senc)
                if check(code_bytes, pos,
                         config['TEXT_FCN'], config['NAME_POS']):  # check if name (0140)
                    marker = 'N'
                    comment = 'NAME'
                    if text not in names:
                        names[text] = ids[marker]
                        ids[marker] += 1
                    numid = names[text]
                elif check(code_bytes, pos,
                           config['TEXT_FCN'], config['TEXT_POS']):  # check if text (0140)
                    marker = 'T'
                    name_dword = get_dword(code_bytes,
                                           pos + config['TEXT_POS'] - config['NAME_POS'])
                    if name_dword != 0:
                        try:
                            name_addr = name_dword - code_size
                            name = text_section[name_addr].decode(bgi_setup.senc)
                            comment = 'TEXT 【%s】' % name
                        except KeyError:
                            comment = 'TEXT'
                    else:
                        comment = 'TEXT'
                    numid = ids[marker]
                    ids[marker] += 1
                elif check(code_bytes, pos,
                           config['RUBY_FCN'], config['RUBYK_POS']):  # check if ruby kanji (014b)
                    marker = 'T'
                    comment = 'TEXT RUBY KANJI'
                    numid = ids[marker]
                    ids[marker] += 1
                elif check(code_bytes, pos,
                           config['RUBY_FCN'],
                           config['RUBYF_POS']):                     # check if ruby furigana (014b)
                    marker = 'T'
                    comment = 'TEXT RUBY FURIGANA'
                    numid = ids[marker]
                    ids[marker] += 1
                elif check(code_bytes, pos,
                           config['BKLG_FCN'], config['BKLG_POS']):  # check if backlog text (0143)
                    marker = 'T'
                    comment = 'TEXT BACKLOG'
                    numid = ids[marker]
                    ids[marker] += 1
                else:
                    marker = 'Z'
                    comment = 'OTHER'
                    if text not in others:
                        others[text] = ids[marker]
                        ids[marker] += 1
                    numid = others[text]
                record = text, numid, marker, comment
                code_section[pos] = record
            elif optype == config['FILE_TYPE']:
                text = text.decode(bgi_setup.senc)
                marker = 'Z'
                comment = 'OTHER'
                if text not in others:
                    others[text] = ids[marker]
                    ids[marker] += 1
                numid = others[text]
                record = text, numid, marker, comment
                code_section[pos] = record
        else:
            # missing text_addr in text_section
            pass
        pos += 4
#    print("%d pos" % len(matched_pos))
    unmatched_strings = {key: value for key, value
                         in text_section.items()
                         if key not in matched_pos}
    return code_section, unmatched_strings
