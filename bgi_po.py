# defines the bgi_po.IndexedPo class
import polib
import datetime

class IndexedPo(polib.POFile):
	def __init__(self, *args, **kwargs):
		"""
		See polib._BaseFile.__init__() for details on arguments
		"""
		super().__init__(*args, **kwargs)
		if self.fpath is None:
			self._init_blank_po()
		else:
			self.count = -1

	def _init_blank_po(self):
		self.count = 0
		try:
			now = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()
		except:
			now = datetime.datetime.now(datetime.timezone.utc).isoformat()

		self.metadata = {
			'Project-Id-Version'  : 'PACKAGE VERSION',
			'Report-Msgid-Bugs-To': '',
			'POT-Creation-Date'   :  now,
			'PO-Revision-Date'    : 'YEAR-MO-DA HO:MI+ZONE',
			'Last-Translator'     : 'FULL NAME <EMAIL@ADDRESS>',
			'Language-Team'       : 'LANGUAGE <LL@li.org>',
			'MIME-Version'        : '1.0',
			'Content-Type'        : 'text/plain; charset=utf-8',
			'Content-Transfer-Encoding': '8bit',
			'X-Generator'         : 'Bgi_script_tools::IndexedPo',
		}

	def add(self, msgctxt, **kwargs):
		if self.count >= 0:  # is_indexed
			kwargs.pop('msgctxt',None)
			kwargs.pop('msgid',None)
			entry = polib.POEntry(
				msgctxt=msgctxt,
				msgid="{:04d}:".format(self.count + 1),
				**kwargs
			)
			self.count = self.count + 1
		else:
			entry = polib.POEntry(**dict(kwargs, msgctxt=msgctxt))
		self.append(entry)

	def set_language(self, langid):
		self.metadata['Language-Team'] = '{0} <{0}@li.org>'.format(langid)
		self.metadata['Language'] = '{}'.format(langid)

	def find_by_prefix(self, st, by='msgid'):
		"""
		Find the entry whose msgid begins with the string ``st``.
		"""
		for e in self:
			if getattr(e, by).startswith(st):
				return e
		return None

