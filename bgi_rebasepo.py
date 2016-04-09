#!/usr/bin/env python3

# Reconcile multiple *.po's with a reference .pot file
# Also rewrite numeric msgid's to a fully-fledged one with original text

import os
import sys
import polib

import bgi_po
import bgi_setup

def rebase_po(source_po):
	"""
		reconcile multiple po's from several slang by making one of them authoritative
		- sync all msgid's
		- overwrite msgctxt
		- leaves comment untouched
	"""
	for subdir in [name for name in os.listdir(bgi_setup.project_name)
	                             if os.path.isdir(os.path.join(bgi_setup.project_name, name))]:
		refpopath = "{}/{}/{}".format(bgi_setup.project_name, subdir, source_po)
		print("Ref: {}".format(refpopath), file=sys.stderr)
		if not os.path.exists(refpopath):
			print("Error: Missing {}\nYou need to generate the template, having (dlang == slang) and (dcopy == True) in bgi_setup.py, and run bgi_dumppo.py once.".format(refpopath))
			sys.exit(1)
		refpot = polib.pofile(refpopath, klass=bgi_po.IndexedPo)
		tlmap = {}
		for refent in refpot:
			tlmap[refent.msgid] = ("{}{}".format(refent.msgid, refent.msgctxt), refent.msgctxt)
		for key in tlmap:
			if key[-1] != ":":
				print("Error: msgid in {} should be in the format '<NUMBER>:'. Make sure you only run this tool once.".format(refpopath), file=sys.stderr)
				sys.exit(1)
			break
		
		for poname in os.listdir(os.path.join(bgi_setup.project_name, subdir)):
			if poname != source_po:
				modpath = "{}/{}/{}".format(bgi_setup.project_name, subdir, poname)
				print("Po: {}".format(modpath), file=sys.stderr)
				modpo = polib.pofile(modpath, klass=bgi_po.IndexedPo)
				mod_entries = dict((entry.msgid, entry) for entry in modpo)
				for oldid,newinfo in tlmap.items():
					e = modpo.find(oldid)
					e.msgid, e.msgctxt = newinfo
				modpo.save()
		for oldid,newinfo in tlmap.items():
			refpot.find(oldid).msgid, _ = newinfo
		refpot.save()

if __name__ == '__main__':
	print("Source lang: {}".format(bgi_setup.slang), file=sys.stderr)
	rebase_po("{}.pot".format(bgi_setup.slang))
