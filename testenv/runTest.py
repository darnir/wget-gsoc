#!/usr/bin/env python

import HTTPServer
import http.client
import xml.etree.ElementTree as ET
import sys
import os
from multiprocessing import Process
from subprocess import call
from time import sleep
from sys import exit

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

for TestCase in sys.argv[1:]:
    if os.path.isfile(TestCase):
        TestTree = ET.parse(TestCase)
        Root = TestTree.getroot()
        inputFile = []
        params = []
        params.append(WgetPath)
        retCode = 0

        for comm in Root.findall('Option'):
           params.append(comm.text)
        for filen in Root.findall('InputFile'):
            inputFile.append(filen.text)
            params.append("localhost:8090/" + filen.get('name'))
        resultsNode = Root.find('ExpectedResults')
        expectedRet = int(resultsNode.find('ReturnCode').text)

        start_server(inputFile)

        # Required to so that Wget is not invoked before the Server is initialized
        sleep(2)
        retCode = call(params)

        print(retCode)
        print(expectedRet)
        if retCode == expectedRet:
            print("Test Passed")
        else:
            print ("Test Failed")

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
