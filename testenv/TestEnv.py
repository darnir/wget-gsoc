import HTTPServer
import http.client
import os
import shutil
import sys
from ColourTerm import printer
from difflib import unified_diff
from xml.etree.ElementTree import parse, ParseError

testdir = ""

""" A custom exception that is raised in the event
that anything goes wrong while processing the test. """
class TestFailed (Exception):
   pass

class Test:
   TestFailed = TestFailed

   def __init__ (self, TestFile):
      try:
         TestTree = parse (TestFile)
      except ParseError as ae:
         raise TestFailed ()
      self.Root = TestTree.getroot ()
      self.testDir = TestFile + "-test"
      self.resultsNode = self.Root.find ('ExpectedResults')
      try:
         os.mkdir (self.testDir)
      except FileExistsError as ae:
         shutil.rmtree (self.testDir)
         os.mkdir (self.testDir)
      os.chdir (self.testDir)

   """ Create an insatnce of the Server. """
   def start_server (self):
      global server
      server = HTTPServer.create_server ()
      port = server.server_address[1]
      global domain
      domain = "localhost:" + str (port) + "/"

   def spawn_server (self):
      HTTPServer.spawn_server (server)

   """ Send a HTTP QUIT Request to stop the Server """
   def stop_server (self):
      conn = http.client.HTTPConnection (domain.strip ('/'))
      conn.request ("QUIT", "/")
      conn.getresponse ()

   def gen_file_list (self):
      self.download_list = ""
      self.file_list = dict ()
      for file_element in self.Root.findall ('InputFile'):
         self.file_list[file_element.get ('name')] = file_element.text
         if file_element.get ('download') == 'False':
            continue
         self.download_list = self.download_list + domain + \
                           file_element.get ('name') + " "
      HTTPServer.mk_file_sys (self.file_list)

   def parse_special (self):
      # Handle redirection Requests
      redirection_list = dict()
      for special_comm in self.Root.findall ('Special'):
         if special_comm.text == "Redirect":
            redir_tuple = [special_comm.get ('to'), special_comm.get ("code")]
            redirection_list[special_comm.get ('from')] = redir_tuple
      HTTPServer.set_server_rules (redirections = redirection_list)

   def get_cmd_line (self, WgetPath):
      cmd_line = WgetPath + " "
      for parameter in self.Root.findall('Option'):
         cmd_line += parameter.text + " "
      cmd_line += self.download_list
      return cmd_line

   def _test_cleanup (self):
      os.chdir("..")
      if os.getenv ("NO_CLEANUP") is None:
         shutil.rmtree(self.testDir)

   def endTest (self):
      self._test_cleanup()

   def test_return_code (self, retCode):
      expected_return_code = int (self.resultsNode.find ('ReturnCode').text)
      if retCode != expected_return_code:
         printer ("RED", "Expected Exit Code: " + str (expected_return_code))
         printer ("RED", "Actual Exit Code:   " + str (retCode))
         self._test_cleanup ()
         raise TestFailed ()

   def _gen_expected_files (self):
      expected_files = dict ()
      for expectedFile in self.resultsNode.findall ('File'):
         origName = expectedFile.get ('orig') if expectedFile.get ('orig') \
                                    else expectedFile.text
         expected_files[expectedFile.text] = origName
      return expected_files

   def test_downloaded_files (self):
      expected_files = self._gen_expected_files()
      # Go through all files in PWD, which is the test directory
      for parent, dirs, files in os.walk ("."):
         for filename in files:
            if filename in expected_files:
               file_handler = open (filename, "r")
               file_content = file_handler.read()
               real_contents = self.file_list.get (expected_files[filename])
               if real_contents != file_content:
                  printer ("RED", "Contents of " + filename + " do not match")
                  for line in unified_diff (real_contents, file_content,
                                          fromfile = "Original", tofile = "Actual"):
                     sys.stderr.write (line)
                  print() # Print empty line for formatting purposes
                  file_handler.close ()
                  self._test_cleanup ()
                  raise TestFailed ()
               del expected_files[filename]
            else:
               printer ("RED", "Extra files downloaded by Wget.")
               self._test_cleanup ()
               raise TestFailed ()
         if expected_files:
            printer ("RED", "Not all expected files were downloaded.")
            printer ("RED", "Missing files: " + str (list (expected_files.keys ())).strip("[']"))
            self._test_cleanup ()
            raise TestFailed ()


# vim: set ts=8 sw=3 sts=3 tw=0 et :
