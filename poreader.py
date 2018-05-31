import polib
import glob
import sys
import os.path
import json

class Reader():
    def read(self, directory):
        voiceDict = {}
        exp = directory + '/**/*.pot'

        for file in glob.glob(exp):
            print('reading %s' % file)
            entries = polib.pofile(file)

            if entries != None:
                print('found %d entries in %s' % (len(entries), file))
                voiceEntries = filter(lambda entry: entry.comment == 'VOICE', entries)
                
                for voiceEntry in voiceEntries:
                    voiceDict[voiceEntry.msgctxt + '.ogg'] = voiceEntry.msgstr

        return voiceDict

    def main(self, directory):
        entries = self.read(directory)
        file = os.path.join(directory, 'entries.json')

        with open(file, 'w') as stream:
            json.dump(entries, stream)

if __name__ == '__main__' and len(sys.argv) == 2:
    Reader().main(sys.argv[1])