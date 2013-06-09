#!/usr/bin/env python

import HTTPServer
import http.client
import xml.etree.ElementTree as ET
import sys
import os
import shlex
from multiprocessing import Process
from subprocess import call
from time import sleep
from sys import exit
from ColourTerm import printer

def stop_server ():
    """send QUIT request to http server running on localhost:<port>"""
    conn = http.client.HTTPConnection("localhost:8090")
    conn.request("QUIT", "/")
    conn.getresponse()

def start_server (inputFile):
    server_process = Process(target=HTTPServer.initServer, args=(inputFile, ))
    server_process.start()

# Build the path to local build of Wget
dirn = os.path.dirname(sys.argv[0])
absp = os.path.abspath(dirn)
WgetPath = absp + "/../src/wget"

# Check for each TestCase file supplied in the arguments.
# It is however preferable to run multiple tests through an external module
# that aggregates the results better.
for TestCase in sys.argv[1:]:
    if os.path.isfile(TestCase):
        TestTree = ET.parse(TestCase)
        Root = TestTree.getroot()
        params = WgetPath + " "
        files = ""
        expectedFiles = []
        retCode = 0
        # Initialize inputFiles as a dictionary.
        # Filename:content pairs.
        inputFiles = dict()

        for filen in Root.findall('InputFile'):
            inputFiles[filen.get('name')] = filen.text
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

        print(retCode)
        print(expectedRet)
        if retCode == expectedRet:
            printer("GREEN","Test Passed.")
        else:
            printer ("RED","Test Failed.")
            printer ("RED","Expected Code: " + str(expectedRet) + ". Return Code: " + str(retCode) + ".")

    else:
       print ("The Test Case File: " + TestCase + " does not exist.")
       exit(24)

# XXX: Check if maybe we can fire the server through the subprocess module and reduce a module dependancy on multiprocessing.
# XXX: Maybe the server should be spawned through subprocess with an open pipe. The server can then inform
#      thr parent script upon initialization. Hence removing the use hard sleep(2) statement.

#Replacement Code. Responsibilities.
# Parse the Test Case File. (In-Progress)
# Send the Required Files to the Server. (Done)
# Create the command line to execute. (Done)
# Read the return code. (Done)
# Decide on Pass or Fail of Test. (TODO)

stop_server()
exit(retCode)
