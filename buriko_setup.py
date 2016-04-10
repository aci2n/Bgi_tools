"""
User-settable settings for Buriko script tools, used across the different Python scripts
"""
import re

project_name = 'itsusora'

# Source encoding
senc = 'CP932'

# Insertion language
ilang = 'en'

# Insertion encoding
ienc = 'CP932'

# Do not modify below code
def is_jis_source():
    return re.search(r'jis|932', senc, re.IGNORECASE) is not None
