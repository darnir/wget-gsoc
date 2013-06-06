#!/usr/bin/env python

import HTTPServer
import http.client
import xml.etree.ElementTree as ET
import sys
import os
from multiprocessing import Process
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
        for filen in Root.findall('InputFile'):
            inputFile.append(filen.text)
        start_server(inputFile)
    else:
       print ("The Test Case File: " + TestCase + " does not exist.")
       exit(1)

#Replacement Code. Responsibilities.
# Parse the Test Case File
# Send the Required Files to the Server.
# Create the command line to execute
# Read the return code
# Decide on Pass or Fail of Test.
sleep(10)
stop_server()
