import HTTPServer
import http.client
import os
import shutil
import sys
from ColourTerm import printer
from difflib import unified_diff
from collections import defaultdict
from xml.etree.ElementTree import parse, ParseError

testdir = ""

""" A custom exception that is raised in the event
that anything goes wrong while processing the test. """
class TestFailed (Exception):
   def __init__ (self, error):
      self.error = error

class Test:
   TestFailed = TestFailed

   def __init__ (self, TestFile):
      try:
         TestTree = parse (TestFile)
      except ParseError as ae:
         raise TestFailed ("Error when parsing " + TestFile + ": " + ae.__str__ ())
      self.Root = TestTree.getroot ()
      if self.Root.tag != "WgetTest":
         raise TestFailed ("Not a valid Test File.")
      printer ("BLUE", "Running Test: " + self.Root.get ('name'))
      self.testDir = TestFile + "-test"
      self.resultsNode = self.Root.find ('ExpectedResults')
      try:
         os.mkdir (self.testDir)
      except FileExistsError as ae:
         shutil.rmtree (self.testDir)
         os.mkdir (self.testDir)
      os.chdir (self.testDir)
      self.download_list = ""

   def init_server (self):
      server = HTTPServer.create_server ()
      port = server.server_address[1]
      domain_name = server.server_address[0]
      self.domain = domain_name + ":" + str (port) + "/"
      server_rules = self.parse_files ()
      server.server_conf (self.file_list, server_rules)
      HTTPServer.spawn_server (server)

   """ Send a HTTP QUIT Request to stop the Server """
   def stop_server (self):
      conn = http.client.HTTPConnection (self.domain.strip ('/'))
      conn.request ("QUIT", "/")
      self.fileSys = HTTPServer.ret_fileSys()
      conn.getresponse ()

   def append_downloads (self, filename):
      self.download_list += self.domain + filename + " "

   def parse_files (self):
      self.file_list = dict ()
      server_rules = dict ()
      for file_node in self.Root.findall ('File'):
         try:
            metadata = file_node.find ('Meta')
            self.filename = metadata.get ('name')
            toDownload = True if metadata.get ('no-download') is None else False
            content_node = file_node.find ('Content')
            if content_node is not None:
               self.file_list[self.filename] = content_node.text
            if toDownload is True:
               self.append_downloads (self.filename)
         except Exception as ae:
            raise TestFailed ("An error occurred: " + ae.__str__ ())
         filerule = self.parse_server_rules (file_node)
         server_rules[self.filename] = filerule
      return server_rules

   class Cust_Header:
      def __init__ (self, header, value):
         self.header_name = header
         self.header_value = value

   class Cookie:
      def __init__ (self, value):
         self.cookie_value = value

   class Resp:
      def __init__ (self, code):
         self.response_code = int (code)

   def get_redir (self):
      redir_to = self.special_comm.find ('To').text
      redir_code = self.special_comm.find ('Code').text
      header_obj = self.Cust_Header ("Location", redir_to)
      response_obj = self.Resp (redir_code)
      return [("Header", header_obj), ("Response", response_obj)]

   def set_cont (self):
      file_handle = open (self.filename, "w")
      offset_node = self.special_comm.find ('Bytes')
      if offset_node is not None:
         offset = int (offset_node.text)
         file_handle.write (self.file_list[self.filename][:offset])
      return [(None, None)]

   def get_cont_disp (self):
      cname = self.special_comm.find ('Name').text
      cheader = "Content-Disposition"
      cvalue = "Attachment; filename=" + cname
      cont_disp_obj = self.Cust_Header (cheader, cvalue)
      return [("Header", cont_disp_obj)]

   def get_header (self):
      header_node = self.special_comm.find ('Name')
      header = header_node.text
      value_node = self.special_comm.find ('Value')
      value = value_node.text
      header_obj = self.Cust_Header (header, value)
      return [("Header", header_obj)]

   def get_cookie (self):
      cookie_list = list()
      for sendCookie in self.special_comm.findall ('Send'):
         send_cookie = self.Cust_Header ('Set-Cookie', sendCookie.text)
         cookie_list.append (("Header", send_cookie))
      for expectCookie in self.special_comm.findall ('Expect'):
         expect_cookie = self.Cookie (expectCookie.text)
         cookie_list.append (("Cookie", expect_cookie))
      return cookie_list

   def get_response (self):
      resp_obj = self.Resp (self.special_comm.find ('Code').text)
      return [("Response", resp_obj)]

   def parse_server_rules (self, file_node):
      special_conf = defaultdict (list)
      self.meth_files = ""
      commands_list = {
         "Redirect":self.get_redir,
         "Continue":self.set_cont,
         "ContentDisposition":self.get_cont_disp,
         "Header":self.get_header,
         "Cookie":self.get_cookie,
         "Response":self.get_response
      }
      for self.special_comm in file_node.findall ('ServerRule'):
         command = self.special_comm.get ('command')
         try:
            rule_obj = commands_list.get(command) ()
         except TypeError as ae:
            raise TestFailed ("Configuration details for Server Rule " + command + " do not exist")
         for name, rule in rule_obj:
            if name is not None:
               special_conf[name].append (rule)
      return special_conf

   def get_cmd_line (self, WgetPath):
      cmd_line = WgetPath + " "
      for parameter in self.Root.findall('Option'):
         cmd_line += parameter.text + " "
      cmd_line += self.download_list
      print (cmd_line)
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
         raise TestFailed ("")

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
               real_contents = self.fileSys.get (expected_files[filename])
               if real_contents != file_content:
                  printer ("RED", "Contents of " + filename + " do not match")
                  for line in unified_diff (real_contents, file_content,
                                          fromfile = "Original", tofile = "Actual"):
                     sys.stderr.write (line)
                  print() # Print empty line for formatting purposes
                  file_handler.close ()
                  self._test_cleanup ()
                  raise TestFailed ("")
               del expected_files[filename]
            else:
               printer ("RED", "Extra files downloaded by Wget.")
               self._test_cleanup ()
               raise TestFailed ("")
         if expected_files:
            printer ("RED", "Not all expected files were downloaded.")
            printer ("RED", "Missing files: " + str (list (expected_files.keys ())).strip("[']"))
            self._test_cleanup ()
            raise TestFailed ("")


# vim: set ts=8 sw=3 sts=3 tw=0 et :
