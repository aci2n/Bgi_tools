#!/usr/bin/env python
# link: http://www.emacswiki.org/emacs/PythonMode#toc7
#
# This is a script which runs and parses the output of various Python code
# checking programs to work with flymake. It has lots of issues, one being that
# flymake does not seem to show more than one error message per line of code,
# meaning that an error or warning which is intentionally left unfixed can mask
# an error or warning that would get more attention.
#
# Additionally, the scripts which check python code are either rather anemic,
# and don't notice too much (pychecker) or are aggressive, and warn about all
# sorts of things that they should not (pylint). pep8.py tends to be annoyingly
# aggressive about whitespace.
#
# You must have pep8.py, pychecker and pylint in PATH for this script to find
# them. Additionally this script attempts to support virtual environments, but
# this is largely untested.

import os
import re
import sys
import os.path

from subprocess import Popen, PIPE
import collections

OUTPUT_FORMAT = "%(filename)s:%(line_number)s: %(level)s:"\
                " %(error_type)s%(error_number)s (%(checker)s) %(description)s"


class LintRunner(object):
    """Provides common functionality to run python code checkers."""

    sane_default_ignore_codes = set([])
    command = None
    output_matcher = None

    #flymake: ("\\(.*\\) at \\([^ \n]+\\) line \\([0-9]+\\)[,.\n]" 2 3 nil 1)
    #or in non-retardate: r'(.*) at ([^ \n]) line ([0-9])[,.\n]'


    def __init__(self, virtualenv=None, pythonpath=None, ignore_codes=(),
                 use_sane_defaults=True, debug=None):
        self.env = {}

        if virtualenv:
            # This is the least we can get away with (hopefully).
            self.env['VIRTUAL_ENV'] = virtualenv
            self.env['PATH'] = virtualenv + ':' + os.environ['PATH']

        if pythonpath:
            ppath = os.environ.get('PYTHONPATH', '')
            if ppath != '':
                pythonpath = pythonpath + ':' + ppath

            self.env['PYTHONPATH'] = pythonpath

        if self.env == {}:
            self.env = None

        self.filename = None
        self.virtualenv = virtualenv
        self.ignore_codes = set(ignore_codes)
        self.use_sane_defaults = use_sane_defaults
        self.debug = debug

    @property
    def operative_ignore_codes(self):
        if self.use_sane_defaults:
            return self.ignore_codes ^ self.sane_default_ignore_codes
        else:
            return self.ignore_codes

    @property
    def run_flags(self):
        return ()

    def fixup_data(self, line, data):
        if 'line_number' in data:
            data['line_number'] = int(data['line_number'])
        return data

    def process_output(self, line):
        lines = []
        m = self.output_matcher.match(line)
        if m:
            fixed_data = dict.fromkeys(('level', 'error_type',
                                        'error_number', 'description',
                                        'filename', 'line_number'),
                                       '')
            fixed_data['checker'] = self.command
            fixed_data.update(self.fixup_data(line, m.groupdict()))
            lines.append(fixed_data)
        elif line and self.debug:
        # write to stderr what seems to not work:
        # may need to be fixed later to parse it properly
            sys.stderr.write("Failed to parse as *%s* output: %r\n" %
                    (self.command, line))

        return lines

    def run(self, filename):
        self.filename = filename
        cmdline = [self.command]
        cmdline.extend(self.run_flags)
        cmdline.append(filename)

        print(' '.join(cmdline))
        # print the binary that will be launched
        if self.debug:
            which_proc = Popen(['which', self.command], stdout=PIPE, stderr=PIPE, env=self.env)
            stdout=''.join(which_proc.stdout.readlines())
            sys.stderr.write("Launching : %s" % stdout)
            sys.stderr.write("cmdline : %s\n\n" % ' '.join(cmdline))

        try:
            process = Popen(cmdline, stdout=PIPE, stderr=PIPE, env=self.env)
        except Exception:
            print("Failed to run command:\n%s" % cmdline)
            raise

        stdoutdata, stderrdata = process.communicate()

        # WARNING: return code different from 0 does not work with pylint
        # (return code = quality of the reported code)
        # But it issues an error code of 1 if a fatal message was issued
        # See: pylint --long-help
        if process.returncode != 0 and self.debug:
            sys.stderr.write(stderrdata)

        lines_data = []
        for line in stdoutdata.decode('ascii', 'ignore').split('\n'):
            lines_data += self.process_output(line)

        return lines_data



class PylintRunner(LintRunner):
    """ Run pylint, producing flymake readable output.

    The raw output looks like:
      render.py:49: [C0301] Line too long (82/80)
      render.py:1: [C0111] Missing docstring
      render.py:3: [E0611] No name 'Response' in module 'werkzeug'
      render.py:32: [C0111, render] Missing docstring
      render.py:8: [F0401] Unable to import 'sact.storage.model' """

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>\d+):'
        r'\s*\[(?P<error_type>[WECRF])'
        r'(?P<error_number>[^,]+),?'
        r'\s*(?P<context>[^\]]*)\]'
        r'\s*(?P<description>.*)$'
        )

    command = 'pylint'

    sane_default_ignore_codes = set([
        "C0103",  # Naming convention
        "C0111",  # Missing Docstring
    #    "E1002",  # Use super on old-style class
        "W0232",  # No __init__
    #    #"I0011",  # Warning locally suppressed using disable-msg
    #    #"I0012",  # Warning locally suppressed using disable-msg
    #    #"W0511",  # FIXME/TODO
         "W0142",  # *args or **kwargs magic.
    #    "R0904",  # Too many public methods
    #    "R0903",  # Too few public methods
    #    "R0201",  # Method could be a function
        ])

    def fixup_data(self, line, data):
        super(self.__class__, self).fixup_data(line, data)

        if data['error_type'].startswith('E'):
            data['level'] = 'ERROR'
        else:
            data['level'] = 'WARNING'

        data['filename'] = self.filename
        return data

    @property
    def run_flags(self):
        return ('--output-format', 'parseable',
                '--include-ids', 'y',
                '--reports', 'n',
                '--rcfile','~/.pylintrc',)
                #'--disable-msg=' + ','.join(self.operative_ignore_codes))


class PycheckerRunner(LintRunner):
    """ Run pychecker, producing flymake readable output.

    The raw output looks like:
      render.py:49: Parameter (maptype) not used
      render.py:49: Parameter (markers) not used
      render.py:49: Parameter (size) not used
      render.py:49: Parameter (zoom) not used """

    command = 'pychecker'

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>\d+):'
        r'\s+(?P<description>.*)$')

    def fixup_data(self, line, data):
        super(self.__class__, self).fixup_data(line, data)

        #XXX: doesn't seem to give the level
        data['level'] = 'WARNING'
        return data

    @property
    def run_flags(self):
        return '--no-deprecated', '-0186', '--only', '-#0'


class Pep8Runner(LintRunner):
    """ Run pep8.py, producing flymake readable output.

    The raw output looks like:
      spiders/structs.py:3:80: E501 line too long (80 characters)
      spiders/structs.py:7:1: W291 trailing whitespace
      spiders/structs.py:25:33: W602 deprecated form of raising exception
      spiders/structs.py:51:9: E301 expected 1 blank line, found 0 """

    command = 'pep8'
    sane_default_ignore_codes = set([
    #     'W391', # blank line at end of file
    #     'W291', # trailing whitespaces
          'E262', # inline comment should start with '# '
    ])

    output_matcher = re.compile(
        r'(?P<filename>.+):'
        r'(?P<line_number>[^:]+):'
        r'[^:]+:'
        r' (?P<error_type>[EW])'
        r'(?P<error_number>\w+) '
        r'(?P<description>.+)$')

    def fixup_data(self, line, data):
        super(self.__class__, self).fixup_data(line, data)

        if 'W' in data['error_number']:
            data['level'] = 'WARNING'
        else:
            data['level'] = 'ERROR'

        return data

    @property
    def run_flags(self):
        return '--repeat', '--ignore=' + ','.join(self.operative_ignore_codes), '--max-line-length=100'


def tweak_options(opts, bin_over_omelette):
    if opts.pythonpath is None and opts.virtualenv is None:
        dirname = os.path.abspath(".")

# look for the bin or the omelette directory
        find = False
        while dirname != "/":
            # look up for the file that fits
            if 'setup.py' in os.listdir(dirname):
                find = True
                break
            dirname = os.path.split(dirname)[0]

# push in the path or the python path the directory needed
        if find:
            ext, opt = bin_over_omelette and \
                            ('bin', 'virtualenv') or \
                            ('parts/omelette', 'pythonpath')

            targetdir = os.path.join(dirname, ext)

            if os.path.exists(targetdir):
                setattr(opts, opt, targetdir)
            else:
                sys.stderr.write("Warning no dir found at %s" % targetdir)


## TODO: Should be detected automatically if "cls.command" is executable in
##       path.
RUNNERS = [PylintRunner, Pep8Runner]
#RUNNERS = [PylintRunner]


if __name__ == '__main__':

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-e", "--virtualenv",
                      dest="virtualenv",
                      default=None,
                      help="virtualenv directory")
    parser.add_option("-i", "--ignore_codes",
                      dest="ignore_codes",
                      default=(),
                      help="error codes to ignore")
    parser.add_option("-p", "--pythonpath",
                      dest="pythonpath",
                      default=None,
                      help="a path to add to PYTHONPATH")
    parser.add_option("-d", "--debug",
                      dest="debug",
                      default=None,
                      action='store_true',
                      help="Add debug log (eg: lines failed to be parsed)")
    options, args = parser.parse_args()

    if len(args) == 0:
        sys.stderr.write("%r requires at least one argument.\n"
                    % os.path.basename(sys.argv[0]))
        sys.exit(1)

    target = args[0]

    ## for pylint : handle if this is a "."
    ## suppose this is a valid file name or a module
#    temp_target = os.path.abspath(target)
#    if os.path.exists(temp_target):
#        target = temp_target

    #tweak_options(options, True)

    ## Extract all options into a dict

    init_args = dict([(k, getattr(options, k))
                      for k in dir(options)
                      if not k.startswith('_') and
                         not isinstance(getattr(options, k), collections.Callable)])

    ## Collect data

    lines_data = []
    for Runner in RUNNERS:
        lines_data += Runner(**init_args).run(target)

    ## Finally print out all errors.

    lines_data.sort(key=lambda x: x['line_number'])
    for line_data in lines_data:
        print(OUTPUT_FORMAT % line_data)

    sys.exit(0)
