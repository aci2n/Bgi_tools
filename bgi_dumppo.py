#!/usr/bin/env python3

# BGI script dumper (to GetText PO)

import glob
import os
import struct
import sys

import bgi_common
import bgi_po
import bgi_setup


def dump_text(fo, marker, id, text, comment, binmode=False):
	fo.write('//%s\n' % comment)
	fo.write('<%s%s%04d>%s\n' % (bgi_setup.slang,marker,id,text))
	for lang in bgi_setup.dlang:
		if bgi_setup.dcopy:
			fo.write('<%s%s%04d>%s\n' % (lang,marker,id,text))
		else:
			fo.write('<%s%s%04d>\n' % (lang,marker,id))
	fo.write('\n')

def dump_bintext(fo, marker, id, text, comment, binmode=True):
	cmt = '//{}\n'.format(comment)
	fo.write(cmt.encode(bgi_setup.denc) if binmode else cmt)
	fo.write(text)
	fo.write('\n'.encode(bgi_setup.denc))

def dump_sequential(fo, code_section, imarker, binmode=False):
	fun = dump_bintext if binmode else dump_text
	for addr in sorted(code_section):
		text, id, marker, comment = code_section[addr]
		if marker == imarker:
			fun(fo, marker, id, text if binmode else bgi_common.escape(text), comment, binmode)
	
def dump_script(script):
	PO_EXT = 'pot' if len(bgi_setup.dlang) == 1 and bgi_setup.dlang[0] == bgi_setup.slang else 'po'

	scriptname = os.path.splitext(os.path.basename(script))[0]
	data = open(script, 'rb').read()
	hdr_bytes, code_bytes, text_bytes, config = bgi_common.split_data(data)
	try:
		code_section, orphan_binstrings = bgi_common.get_code_section(code_bytes, text_bytes, config)
	except bgi_common.BgiCustomException as exc:
		print(str(exc), file=sys.stderr)
		exit(1)
	po = bgi_po.IndexedPo()  # may specify encoding='utf-8-sig' for WinMerge but non-conforming
	for addr in sorted(code_section):
		text, id, marker, comment = code_section[addr]
		if marker=='N':
			prefillmsg = "NAME:{}".format(bgi_common.escape(text))
		elif marker=='Z':
			continue  # dumped as binary later
		else:
			prefillmsg = bgi_common.escape(text) if bgi_setup.dcopy else '' 
		po.add(
			bgi_common.escape(text),
			msgstr=prefillmsg,
			comment=comment
		)
	bgi_common.makedir('{}/{}'.format(bgi_setup.project_name, scriptname))
	for lang in bgi_setup.dlang:
		po.set_language(lang);
		po.save(fpath='{}/{}/{}.{}'.format(bgi_setup.project_name, scriptname, lang, PO_EXT))

	with open(script+'.Z_strings', 'w', encoding=bgi_setup.denc) as outz:
		dump_sequential(outz, code_section, 'Z')
	if os.path.getsize(script+'.Z_strings') == 0:
		os.unlink(script+'.Z_strings')
	if len(orphan_binstrings) > 0:
		print("{} orphan strings written to separate .orphans file.".format(len(orphan_binstrings)), file=sys.stderr)
		with open(script+'.orphans', 'wb') as outo:
			for addr in sorted(orphan_binstrings):
				dump_bintext(outo, None, None, orphan_binstrings[addr], "MIS{:04X}".format(addr))

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print('Usage: bgi_dumppo.py <file(s)>')
		print('(only extension-less files amongst <file(s)> will be processed)')
		sys.exit(1)
	for arg in sys.argv[1:]:
		for script in glob.glob(arg):
			base, ext = os.path.splitext(script)
			if not ext and os.path.isfile(script):
				#print('Dumping %s...' % script)
				dump_script(script)
