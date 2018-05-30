import polib
import glob
import sys

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
                    voiceDict[voiceEntry.msgctxt] = voiceEntry.msgstr

        return voiceDict

if __name__ == '__main__' and len(sys.argv) == 2:
    print(Reader().read(sys.argv[1]))