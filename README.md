Bgi_tools
=========

Based on kingshriek's tools (see upstream repos https://github.com/mchubby-3rdparty/Bgi_script_tools and https://github.com/mchubby-3rdparty/Bgi_asdis)

Thanks to his extensive work (bgi_config.py), this repository targets the **BGI / Ethornell 1.66** engine.


Step 0. Setup (Windows)
-----------------------

### A general-purpose Editor
I recommend Notepad++.


### Python
- Download and install a Python 3.x release (x86 or x86-64 does not matter) from https://www.python.org/downloads/

In the setup wizard, make sure "**pip**" is installed -- it is enabled by default.

- Open a Powershell command prompt (open Windows menu and type "powershell" then click on its icon).
Powershell is included in all editions of Windows 7 through Windows 10.

- Type (change "Python34" to match your local Python install):
```
cd C:\Python34\Scripts
.\pip.exe install polib
```

Then, close the command prompt.

### Code Repository ("your local repo")

- Obtain a copy of this code repository from Github. You may use the "Download ZIP" button as a convenience.
Then, unzip the downloaded archive onto your computer and browse to that folder in Explorer.

The repository contains helper powershell scripts with a .ps1 file extension.

- R-click on *_1-dumppo-all.ps1* and select *Edit* in the contextual menu. It will open the file either in Notepad, or in "Windows Powershell ISE."
- Modify the `$Python = "C:\Python34\python.exe"` line according to your Python location, then save.
- Repeat the process for each .ps1 script.


Step 1. Extract original scripts ("BGI scripts")
------------------------------------------------

(Note: ExtractData 1.20 produces corrupted files when extracting headerless BGI .arc's, do not use it)
- Copy the game archive *data010.arc* to "your local repo"
- Download and extract the latest binary release (= with .exe) of rr-'s arc_unpacker from https://github.com/vn-tools/arc_unpacker/releases
- Copy *arc_unpacker.exe* to "your local repo"
- Open a Powershell command prompt and change dir to "your local repo"
  example: `cd C:\EXTRACT\bgilab`
- Extract all files with the following command:
  `.\arc_unpacker.exe --dec=bgi/arc data010.arc`
- Rename the files to their correct extension:
```
cd data010~.arc
dir *.dat | rename-item -newname { [io.path]::ChangeExtension($_.name, "") }
move * ..
exit
```

Step 2. Dump BGI script resources to Gettext localization format (".po files")
------------------------------------------------------------------------------

### Generate source lang po template ("*.pot")

- R-click on **bgi_setup.py** and open with your text editor (*Edit with Notepad++*)
- You may review the settings. By default, the script will generate a PO Template when `slang = 'ja'` and `dlang = ['ja']` and `dcopy = True`
- R-click on *_1-dumppo-all.ps1* and select "Run with Powershell".
If there are errors during the dumping process, you either hit a bug, scripts are malformed, or target a different BGI engine version.
- All files are extracted in a folder named after the `project_name` in **bgi_setup.py** (the "project folder").
There is a subfolder matching each script file, and they contain a "ja.pot" template.

If you need to dump a particular script in Powershell:
```
& "C:\Python34\python.exe" bgi_dumppo.py Scenario1234
```

### Generate destination lang po ("*.po")

- Go back to **bgi_setup.py** in the text editor. Now set `dlang = ['en']` and `dcopy = False`
- R-click on *_1-dumppo-all.ps1* and select "Run with Powershell".
All subfolders should now contain an "en.po" file.

- R-click on *_2-rebasepo-all.ps1* and select "Run with Powershell".
This script should only be run once (it alters both *.pot and *.po files), lest you have to restart the whole step.
A failsafe mechanism will prevent it from running several times.


Step 3. Translate .po files
---------------------------

There are plenty options here and it's a bit out of scope for this readme.
The most prominent one for offline localization is [Poedit][1].

For web-based collaborative localization, I suggest installing the self-hosted [Weblate][2] software on a Python/Django webserver.
It has a demo at https://demo.weblate.org/.

[1] https://poedit.net/
[2] https://weblate.org/


Step 4. Disassemble BGI scripts (".bsd bytecode")
-------------------------------------------------

- Edit *buriko_setup.py* and review the settings
- R-click on *_3-dis-all.ps1* and select "Run with Powershell".
A multitude of *.bsd shall be produced in the "project folder".
You do not need to edit them.


Step 5. Assemble BGI scripts ("Recompiling")
--------------------------------------------

- Edit *buriko_setup.py* and review the insertion settings
- Copy each updated *.po into its respective subfolder
- Edit *_4-as-all.ps1* and change the `$RootDir` variable to match your "project folder"
- R-click on *_4-dis-all.ps1* and select "Run with Powershell".
A "compiled" subfolder should appear in the "project folder", containing recompiled files (Scenario* files with no extension)

If you need to compile a particular script in Powershell:
```
& "C:\Python34\python.exe" bgias.py project/Scenario1234.bsd
```


Step 6. Recreate data010.arc ("Repacking")
------------------------------------------

TODO. See https://github.com/polaris-/vn_translation_tools/

You may also copy the files in compiled/Scenario* directly besides the game executable.


Step 7. In-game Layout
----------------------

TODO. You probably need to patch or hook the game executable to handle UTF8 (if Shift JIS is not sufficient), VFW and line breaks.


