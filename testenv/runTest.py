#!/usr/bin/env python

import sys
import os
import shlex
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
    if os.path.isfile(TestCase):
        Root = init_test_env(TestCase)
        params = WgetPath + " "
        files = ""
        expectedFiles = []
        retCode = 0
        # Initialize inputFiles as a dictionary.
        # Filename:content pairs.
        inputFiles = dict()

        for filen in Root.findall('InputFile'):
            inputFiles[filen.get('name')] = filen.text
            if filen.get('download') == 'True':
                files = files + "localhost:8090/" + filen.get('name') + " "

        # Spawn the server as early as possible. This gives time for the server
        # to initialize before we call Wget. Hopefully we can do away with sleep(2) soon.
        # This will become more prominent as larger amount of parsing and other code is implemented.
        start_server(inputFiles)

        for comm in Root.findall('Option'):
           params = params + comm.text + " "
        resultsNode = Root.find('ExpectedResults')
        expectedRet = int(resultsNode.find('ReturnCode').text)
        for expFile in resultsNode.findall('File'):
            expectedFiles.append(expFile.text)

        params = params + files
        parameters = shlex.split(params)

        # Required to so that Wget is not invoked before the Server is initialized
        sleep(2)
        retCode = call(parameters)
        stop_server()

        if retCode != expectedRet:
            printer ("RED","Test Failed.")
            printer ("RED","Expected Code: " + str(expectedRet) + ". Return Code: " + str(retCode) + ".")
            exit_test(retCode)

        try:
            FileHandler = ""
            for File_d in expectedFiles:
                FileHandler = open(File_d, "r")
                FileContent = FileHandler.read()
                if (inputFiles.get(File_d) != FileContent):
                    FileHandler.close()
                    os.remove(File_d)
                    printer ("RED","Contents of " + File_d + " do not match")
                    exit_test(25)
                FileHandler.close()
                os.remove(File_d)
        except IOError as ae:
            printer("RED", str(ae))
            exit_test(26)

        for parent, dirs, files in os.walk(dirn+"/"+testdir):
            if files:
                printer ("RED", "Extra files downloaded by Wget.")
                printer ("RED", str(files).strip('[]'))
                exit_test(27)

        # If script reaches here, then all Validity tests have passed. The Test was successful.
        printer ("GREEN","Test Passed")

    else:
       print ("The Test Case File: " + TestCase + " does not exist.")
       exit(24)

# TODO: The expected downloaded file names may not match the input file names. (-O option).

exit_test(0)
