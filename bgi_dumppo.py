#!/usr/bin/env python3
"""
Dumps a BGI script to GetText PO
"""
import glob
import os
import sys

import bgi_common
import bgi_po
import bgi_setup


def dump_text(filebuf, marker, numid, text, comment, binmode=False):  # pylint: disable=unused-argument
    """
    Write a record to the specified builtin text file object ``filebuf``
    ``binmode`` is ignored
    Returns: None
    """
    filebuf.write('//%s\n' % comment)
    filebuf.write('<%s%s%04d>%s\n' % (bgi_setup.slang, marker, numid, text))
    for lang in bgi_setup.dlang:
        if bgi_setup.dcopy:
            filebuf.write('<%s%s%04d>%s\n' % (lang, marker, numid, text))
        else:
            filebuf.write('<%s%s%04d>\n' % (lang, marker, numid))
    filebuf.write('\n')


def dump_bintext(filebuf, marker, numid, text, comment, binmode=True):  # pylint: disable=unused-argument
    """
    Write a record to the specified builtin binary file object ``filebuf``
    ``binmode`` must be set accordingly to the file object type
    ``text`` is written as-is (not encoded to a particular representation)
    Returns: None
    """
    cmt = '//{}\n'.format(comment)
    filebuf.write(cmt.encode(bgi_setup.denc) if binmode else cmt)
    filebuf.write(text)
    filebuf.write('\n'.encode(bgi_setup.denc))


def dump_sequential(filebuf, code_section, imarker, binmode=False):
    """
    Dump records to file object ``filebuf`` without caring for duplicated ones
    ``binmode`` must be set accordingly to the file object type
    Returns: None
    """
    writer_fun = dump_bintext if binmode else dump_text
    for addr in sorted(code_section):
        text, numid, marker, comment = code_section[addr]
        if marker == imarker:
            writer_fun(filebuf, marker, numid,
                       text if binmode else bgi_common.escape(text), comment, binmode)


def register_translations(indexedpo, code_dictionary):
    """
    Add translations to PO file based on analysis of code section
    Returns: None
    """
    voice = None
    prev_text = None

    for addr in sorted(code_dictionary):
        text, _, marker, comment = code_dictionary[addr]

        if text == "_PlayVoice":
            voice = prev_text
       
        prev_text = text

        if marker == 'N':
            prefillmsg = "NAME:{}".format(bgi_common.escape(text))
        elif marker == 'Z':
            continue  # not processed here
        else:
            prefillmsg = bgi_common.escape(text) if bgi_setup.dcopy else ''

            if voice != None:
                indexedpo.add(
                    bgi_common.escape(voice),
                    msgstr=prefillmsg,
                    comment='VOICE'
                )
                voice = None

        indexedpo.add(
            bgi_common.escape(text),
            msgstr=prefillmsg,
            comment=comment
        )


def do_extra_diags(scriptpath, code_dictionary, orph_bstrs):
    """
    Write extra (debug) files for analysis/diagnostics
    """
    with open(scriptpath + '.Z_strings', 'w', encoding=bgi_setup.denc) as outz:
        dump_sequential(outz, code_dictionary, 'Z')
    if os.path.getsize(scriptpath + '.Z_strings') == 0:
        os.unlink(scriptpath + '.Z_strings')
    if len(orph_bstrs) > 0:
        print("{} orphan strings written to separate .orphans file.".format(len(orph_bstrs)),
              file=sys.stderr)
        with open(scriptpath + '.orphans', 'wb') as outo:
            for addr in sorted(orph_bstrs):
                dump_bintext(outo, None, None, orph_bstrs[addr], "MIS{:04X}".format(addr))


def dump_script(scriptpath):
    """
    Open and process a BGI script
    Output a .po localization file in a specific subfolder (automatically created)
    """
    po_ext = 'pot' if len(bgi_setup.dlang) == 1 and bgi_setup.dlang[0] == bgi_setup.slang else 'po'

    scriptname = os.path.splitext(os.path.basename(scriptpath))[0]
    data = open(scriptpath, 'rb').read()
    _, code_bytes, text_bytes, config = bgi_common.split_data(data)
    try:
        state = bgi_common.CodeSectionState()
        code_section, orph_bstrs = state.get_code_section(code_bytes, text_bytes, config)
    except bgi_common.BgiCustomException as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    idxpo = bgi_po.IndexedPo()  # may specify encoding='utf-8-sig' for WinMerge but non-conforming
    register_translations(idxpo, code_section)
    # Write po for each destination language
    bgi_common.makedir('{}/{}'.format(bgi_setup.project_name, scriptname))
    for lang in bgi_setup.dlang:
        idxpo.set_language(lang)
        idxpo.save(fpath='{}/{}/{}.{}'.format(bgi_setup.project_name, scriptname, lang, po_ext))
    do_extra_diags(scriptpath, code_section, orph_bstrs)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: bgi_dumppo.py <file(s)>')
        print('(only extension-less files amongst <file(s)> will be processed)')
        sys.exit(1)
    for arg in sys.argv[1:]:
        for script in glob.glob(arg):
            base, ext = os.path.splitext(script)
            if not ext and os.path.isfile(script):
                # print('Dumping %s...' % script)
                dump_script(script)
