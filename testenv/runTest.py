#!/usr/bin/env python3

import sys
import shlex
import os.path
import argparse
from time import sleep
from subprocess import call
from ColourTerm import printer
from TestEnv import Test, TestFailed


""" Initialize Argument Parser. """

parser = argparse.ArgumentParser (
    description="Runner script for Wget Test Environment")

""" Add list of Optional and Positional Parameters. """

# Positional Parameter
files_help = "Names of the Test File(s) to execute"
parser.add_argument ("Files", help=files_help, nargs='+')
# Optional Parameters
s_help = "Only spawn Server with given Test configs."
parser.add_argument ("-s", "--only-server", help=s_help, action="store_true")
parser.add_argument ("-e", "--external", help="Specify path to executable")

args = parser.parse_args ()

""" Build the path to Wget Executable. """
if args.external:
    WGET_PATH = args.external
else:
    ABS_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))
    WGET_PATH = os.path.join(ABS_PATH, "..", "src", "wget")

EXIT_STATUS = 0

""" Check for each TestCase file supplied in the arguments.

It is however preferable to run multiple tests through an external module that
aggregates the results better.

"""

for TestCase in args.Files:
    if os.path.isfile(TestCase):
        try:
            TestObj = Test(TestCase)
            TestObj.init_server()
        except TestFailed as ae:
            printer("PURPLE", "Error encountered.")
            printer("PURPLE", ae.error)
            EXIT_STATUS = 99
            continue

        params = TestObj.get_cmd_line(WGET_PATH)
        parameters = shlex.split(params)

        if args.only_server is True:
            sleep (10000)
            TestObj.endTest ()
            sys.exit (0)
        retCode = call(parameters)
        TestObj.stop_server()

        try:
            TestObj.test_return_code(retCode)
            TestObj.test_downloaded_files()
        except TestFailed:
            printer("RED", "Test Failed")
            EXIT_STATUS = 100
        else:
            printer("GREEN", "Test Passed")
            TestObj.endTest()

    else:
        p_str = "The Test Case File: " + TestCase + " does not exist."
        printer("PURPLE", p_str)
        EXIT_STATUS = 99

sys.exit(EXIT_STATUS)

# vim: set ts=8 sw=3 tw=0 et :
