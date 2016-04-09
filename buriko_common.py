"""
Common routines for handling Buriko scripts
"""

import os
import errno


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
