#!/usr/bin/env python3

import sys
import shlex
import os.path
from time import sleep
from subprocess import call
from ColourTerm import printer
from TestEnv import Test, TestFailed

# Build the path to local build of Wget
ABS_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))
WGET_PATH = os.path.join(ABS_PATH, "..", "src", "wget")

EXIT_STATUS = 0

# Check for each TestCase file supplied in the arguments.
# It is however preferable to run multiple tests through an external module
# that aggregates the results better.
for TestCase in sys.argv[1:]:
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

        # Required to so that Wget is not invoked before the Server is initialized
        #sleep (10000)
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
        printer("PURPLE", "The Test Case File: " +
                TestCase + " does not exist.")
        EXIT_STATUS = 99

sys.exit(EXIT_STATUS)
# vim: set ts=8 sw=3 tw=0 et :
