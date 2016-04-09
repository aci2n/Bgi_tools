"""
bgi_po.IndexedPo class for i18n
"""

import datetime
import polib


class IndexedPo(polib.POFile):
    """
    Adds extra methods to polib.POFile

    Usage:
    when reading from FS
      po = polib.pofile(pathstr, klass=bgi_po.IndexedPo)
    when creating
      po = bgi_po.IndexedPo()
      po.save(pathstr)
    """

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
        except AttributeError:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        self.metadata = {
            'Project-Id-Version': 'PACKAGE VERSION',
            'Report-Msgid-Bugs-To': '',
            'POT-Creation-Date': now,
            'PO-Revision-Date': 'YEAR-MO-DA HO:MI+ZONE',
            'Last-Translator': 'FULL NAME <EMAIL@ADDRESS>',
            'Language-Team': 'LANGUAGE <LL@li.org>',
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Transfer-Encoding': '8bit',
            'X-Generator': 'Bgi_script_tools::IndexedPo',
        }

    def add(self, msgctxt, **kwargs):
        """
        Add a message, while internally  incrementing the counter.
        Should be preferred over parent class method `append()`
        """
        if self.count >= 0:  # is_indexed
            kwargs.pop('msgctxt', None)
            kwargs.pop('msgid', None)
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
        """
        Set language headers in the po file metadata
        """
        self.metadata['Language-Team'] = '{0} <{0}@li.org>'.format(langid)
        self.metadata['Language'] = '{}'.format(langid)

    def find_by_prefix(self, searchterm, by='msgid'):
        """
        Find the entry whose msgid begins with the string ``searchterm``.
        """
        for entry in self:
            if getattr(entry, by).startswith(searchterm):
                return entry
        return None
