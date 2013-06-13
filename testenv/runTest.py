#!/usr/bin/env python

import xml
import sys
import shlex
from os.path import isfile
from subprocess import call
from time import sleep
from sys import exit
from ColourTerm import printer
from TestEnv import *

# Build the path to local build of Wget
dirn = os.path.dirname(sys.argv[0])
absp = os.path.abspath(dirn)
WgetPath = absp + "/../src/wget"

# Check for each TestCase file supplied in the arguments.
# It is however preferable to run multiple tests through an external module
# that aggregates the results better.
for TestCase in sys.argv[1:]:
    if isfile(TestCase):
        try:
            TestObj = Test(TestCase)
        except xml.etree.ElementTree.ParseError:
            printer ("RED", "Parse error in Test Case file.")
            continue

        inputFiles = TestObj.gen_file_list()

        start_server(inputFiles)

        params = TestObj.get_cmd_line(WgetPath)
        parameters = shlex.split(params)

        # Required to so that Wget is not invoked before the Server is initialized
        sleep(2)
        retCode = call(parameters)
        stop_server()

        try:
            TestObj.test_return_code(retCode)
            TestObj.test_downloaded_files()
        except TestFailed:
            printer ("RED", "Test Failed")
        else:
            printer ("GREEN", "Test Passed")
            TestObj.endTest()

    else:
       print ("The Test Case File: " + TestCase + " does not exist.")
