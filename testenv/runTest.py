#!/usr/bin/env python3

import sys
import shlex
from os.path import isfile
from subprocess import call
from time import sleep
from sys import exit
from ColourTerm import printer
from TestEnv import *

# Build the path to local build of Wget
dirn = os.path.dirname (sys.argv[0])
absp = os.path.abspath (dirn)
WgetPath = absp + "/../src/wget"

exit_status = 0

# Check for each TestCase file supplied in the arguments.
# It is however preferable to run multiple tests through an external module
# that aggregates the results better.
for TestCase in sys.argv[1:]:
   if isfile (TestCase):
      try:
         TestObj = Test (TestCase)
      except TestFailed:
         printer ("RED", "Parse error in Test Case file.")
         printer ("RED", "Test Skipped")
         exit_status = 77
         continue

      TestObj.start_server ()

      TestObj.gen_file_list ()
      TestObj.parse_special ()
      TestObj.spawn_server ()
      params = TestObj.get_cmd_line (WgetPath)
      parameters = shlex.split (params)

      # Required to so that Wget is not invoked before the Server is initialized
      #sleep (2)
      retCode = call (parameters)
      TestObj.stop_server ()

      try:
         TestObj.test_return_code (retCode)
         TestObj.test_downloaded_files ()
      except TestFailed:
         printer ("RED", "Test Failed")
         exit_status = 100
      else:
         printer ("GREEN", "Test Passed")
         TestObj.endTest ()

   else:
      print ("The Test Case File: " + TestCase + " does not exist.")
      exit_status = 77

exit (exit_status)
# vim: set ts=8 sw=3 tw=0 et :
