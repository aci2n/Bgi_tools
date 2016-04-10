"""
User-settable settings for BGI script tools, used across the different Python scripts
"""
import re

project_name = 'itsusora'

# Source language
slang = 'ja'

# Destination languages.
dlang = ['ja']

# Insertion language
ilang = 'en'

# Dump file extension
dext = '.txt'

# Source encoding
senc = 'cp932'

# Dump file encoding
denc = 'utf-8'

# Insertion encoding
ienc = 'cp932'

# Copy source line to destination lines (blank line if set to false)
dcopy = True


# Do not modify below code
def is_jis_source():
    return re.search(r'jis|932', senc, re.IGNORECASE) is not None
