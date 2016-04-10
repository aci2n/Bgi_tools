"""
Common routines for handling Buriko scripts
"""

import os
import errno
import struct

import buriko_setup


class BurikoCustomException(Exception):
    """
    Exception type encloses a string describing a generic error occuring
    while processing a Buriko script.
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


def escape_private_sequence(data):
    """
    Escape a non-standard DBCS char outside of cp932 (not private area either)
    Expects a 2-byte long bytes string
    Example: b"\xFF\x03"
    Returns: bytes
    """
    value = struct.unpack('>H', data)[0]
    return '&#{:04X}'.format(value).encode("ASCII")  # len() of this string must be an even number


def get_escaped_text(text):
    """
    Escape all 0xFF.. sequences
    Returns: bytes
    """
    if buriko_setup.is_jis_source():
        while (text.find(b'\xFF') % 2) == 0:
            pvofs = text.find(b'\xFF')
            text = text[:pvofs] + \
                escape_private_sequence(text[pvofs:pvofs + 2]) + \
                text[pvofs + 2:]
    return text


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
