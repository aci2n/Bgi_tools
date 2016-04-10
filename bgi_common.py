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


def escape_private_sequence(data):
    """
    Escape a non-standard DBCS char outside of cp932 (not private area either)
    Expects a 2-byte long bytes string
    Example: b"\xFF\x03"
    Returns: bytes
    """
    value = struct.unpack('>H', data)[0]
    return '&#{:04X}'.format(value).encode("ASCII")  # len() of this string must be an even number


def unescape_private_sequence(value):
    """
    `value` must be a bytes representation in target encoding bgi_setup.ienc
    """
    while True:
        seqofs = value.find(b"&#")
        if seqofs == -1:
            break
        hexval = value[seqofs + 2: seqofs + 6].decode('ASCII')
        value = value[:seqofs] + bytes(bytearray.fromhex(hexval)) + value[seqofs + 6:]
    return value


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


def _get_escaped_text(text):
    """
    Escape all 0xFF.. sequences
    Returns: bytes
    """
    if bgi_setup.is_jis_source():
        while (text.find(b'\xFF') % 2) == 0:
            pvofs = text.find(b'\xFF')
            text = text[:pvofs] + \
                escape_private_sequence(text[pvofs:pvofs + 2]) + \
                text[pvofs + 2:]
    return text


class CodeSectionState:
    """
    Usage:
      state = bgi_common.CodeSectionState()
      a, b = state.get_code_section(code_bytes, text_bytes, config)
    """

    def __init__(self):
        """
        Create properties with dummy values
        """
        self._initialize_state(None, None, None)

    def get_code_section(self, code_bytes, text_bytes, config):
        """
        Parses the BGI code buffer and associates offsets to misc info.
        Also detects orphaned strings (unused strings in `text_bytes`)
        Returns: tuple (dict {offset: RECORD}, dict {offset: bytes})
        """
        self._initialize_state(code_bytes, text_bytes, config)
        code_section = {}
        matched_pos = {}
        pos = 4
        while pos < len(code_bytes):
            optype = get_dword(code_bytes, pos - 4)
            dword = get_dword(code_bytes, pos)
            text_addr = dword - len(code_bytes)
            # check if address is in text section and data type is string or file
            if text_addr in self.text_section:
                matched_pos[text_addr] = True
                text = self.text_section[text_addr]
                if optype == config['STR_TYPE']:
                    text = _get_escaped_text(text).decode(bgi_setup.senc)
                    code_section[pos] = self._make_record_for_strtype(text, pos)
                elif optype == config['FILE_TYPE']:
                    text = text.decode(bgi_setup.senc)
                    code_section[pos] = self._make_record_for_filetype(text)
            pos += 4
        unmatched_strings = {key: value for key, value
                             in self.text_section.items()
                             if key not in matched_pos}
        return code_section, unmatched_strings

    def _initialize_state(self, code_bytes, text_bytes, config):
        self.code_bytes = code_bytes
        self.config = config
        self.text_section = None
        if text_bytes is not None:
            self.text_section = get_text_section(text_bytes, False)
        self.ids = {'N': 1, 'T': 1, 'Z': 1}
        self.names = {}
        self.others = {}

    def _get_id_and_increment(self, markertype):
        numid = self.ids[markertype]
        self.ids[markertype] += 1
        return numid

    def _make_record_for_strtype(self, text, pos):
        """
        Handle a subcase of get_code_section()
        """
        if check(self.code_bytes, pos,
                 self.config['TEXT_FCN'], self.config['NAME_POS']):  # check if name (0140)
            marker = 'N'
            comment = 'NAME'
            if text not in self.names:
                self.names[text] = self._get_id_and_increment(marker)
            numid = self.names[text]
        elif check(self.code_bytes, pos,
                   self.config['TEXT_FCN'], self.config['TEXT_POS']):  # check if text (0140)
            marker = 'T'
            name_dword = get_dword(self.code_bytes,
                                   pos + self.config['TEXT_POS'] - self.config['NAME_POS'])
            if name_dword != 0:
                try:
                    name_addr = name_dword - len(self.code_bytes)
                    name = self.text_section[name_addr].decode(bgi_setup.senc)
                    comment = 'TEXT 【%s】' % name
                except KeyError:
                    comment = 'TEXT'
            else:
                comment = 'TEXT'
            numid = self._get_id_and_increment(marker)
        elif check(self.code_bytes, pos,
                   self.config['RUBY_FCN'], self.config['RUBYK_POS']):  # check if ruby kanji (014b)
            marker = 'T'
            comment = 'TEXT RUBY KANJI'
            numid = self._get_id_and_increment(marker)
        elif check(self.code_bytes, pos,
                   self.config['RUBY_FCN'],
                   self.config['RUBYF_POS']):                     # check if ruby furigana (014b)
            marker = 'T'
            comment = 'TEXT RUBY FURIGANA'
            numid = self._get_id_and_increment(marker)
        elif check(self.code_bytes, pos,
                   self.config['BKLG_FCN'],
                   self.config['BKLG_POS']):                      # check if backlog text (0143)
            marker = 'T'
            comment = 'TEXT BACKLOG'
            numid = self._get_id_and_increment(marker)
        else:
            marker = 'Z'
            comment = 'OTHER'
            if text not in self.others:
                self.others[text] = self._get_id_and_increment(marker)
            numid = self.others[text]
        return text, numid, marker, comment  # record

    def _make_record_for_filetype(self, text):
        """
        Handle a subcase of get_code_section()
        """
        marker = 'Z'
        comment = 'OTHER'
        if text not in self.others:
            self.others[text] = self._get_id_and_increment(marker)
        numid = self.others[text]
        return text, numid, marker, comment  # record
