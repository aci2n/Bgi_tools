"""
Common assembler/disassembler routines.
This module is meant to be imported.
"""
import re

comma_replace     = '@@@z@@Q@@@'
quote_replace     = '$$$q$$H$$$'
backslash_replace = '###g##V###'

re_label = re.compile(r'([A-Za-z_][A-Za-z0-9_]+):$')
re_instr = re.compile(r'([A-Za-z_][A-Za-z0-9_:]*)\((.*)\);$')
re_header = re.compile(r'#header\s+"(.+)"')
re_define = re.compile(r'#define\s+([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)')


class QuoteMismatch(Exception):
    """
    Raised when a closing quote was not found
    """
    pass


class InvalidInstructionFormat(Exception):
    """
    Raised when an instruction is misformed
    """
    pass


class InvalidFunction(Exception):
    """
    Raised when an instruction contains an unknown function
    """
    pass


def escape(text):
    """
    Escape text when writing to file
    Returns: str
    """
    text = text.replace('\\', '\\\\')
    text = text.replace('\a', '\\a')
    text = text.replace('\b', '\\b')
    text = text.replace('\t', '\\t')
    text = text.replace('\n', '\\n')
    text = text.replace('\v', '\\v')
    text = text.replace('\f', '\\f')
    text = text.replace('\r', '\\r')
    text = text.replace('"', '\\"')
    return text


def unescape(text):
    """
    Reverse operation of escape()
    Returns: str
    """
    text = text.replace('\\\\', backslash_replace)
    text = text.replace('\\a', '\a')
    text = text.replace('\\b', '\b')
    text = text.replace('\\t', '\t')
    text = text.replace('\\n', '\n')
    text = text.replace('\\v', '\v')
    text = text.replace('\\f', '\f')
    text = text.replace('\\r', '\r')
    text = text.replace('\\"', '"')
    text = text.replace(backslash_replace, '\\')
    return text


def remove_comment(line):
    """
    Strips any trailing whitespace and comments
    Returns: str
    """
    cpos = 0
    while True:
        cpos = line.find('//', cpos)
        if cpos == -1:
            return line.rstrip()
        qcount = line[:cpos].count('"') - line[:cpos].count('\\"')
        if qcount % 2 == 0:
            break
        cpos += 1
    line = line[:cpos]
    return line.rstrip()


def get_quotes(line):
    """
    Finds all occurrences of quote character
    Returns: array of integers
    """
    pos = 0
    quotes = []
    while True:
        pos = line.find('"', pos)
        if pos == -1:
            break
        quotes.append(pos)
        pos += 1
    return quotes


def replace_quote_commas(line, quotes):
    pos = 0
    commas = []
    while True:
        pos = line.find(',', pos)
        if pos == -1:
            break
        for squote, equote in zip(quotes[::2], quotes[1::2]):
            if squote < pos < equote:
                commas.append(pos)
                break
        pos += 1
    commas.reverse()
    for pos in commas:
        line = line[:pos] + comma_replace + line[pos + 1:]
    return line
