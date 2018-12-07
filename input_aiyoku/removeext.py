import glob
import os

for file in glob.glob("*.dat"):
    noext, _ = os.path.splitext(file)
    print(noext)
    os.rename(file, noext)