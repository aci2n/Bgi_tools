# Common routines for handling Buriko scripts

import os
import sys
import errno

import buriko_setup

class BurikoCustomException(Exception):
	pass

def makedir(dirname):
	try:
		os.makedirs(dirname)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(dirname):
			pass
		else: raise

def get_section_boundary(data):
	pos = -1
	# This is somewhat of a kludge to get the beginning of the text section as it assumes that the
	# code section ends with the byte sequence: 1B 00 00 00 (this is probably a return or exit command).
	while 1:
		res = data.find(b'\x1B\x00\x00\x00', pos+1)
		if res == -1:
			break
		pos = res
	return pos + 4

