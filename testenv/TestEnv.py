import HTTPServer
import FTPServer
import http.client
import os
import shutil
import sys
import FTPServer as FTP
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
            e_str = "Error when parsing " + TestFile + ": " + ae.__str__ ()
            raise TestFailed (e_str)
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
        s_type = self.Root.get ('server')
        self.server_type = "HTTP" if s_type is None else s_type
        server_func = "init_" + self.server_type + "_server"
        assert hasattr (self, server_func)
        getattr (self, server_func) ()

    def init_HTTP_server (self):
        server = HTTPServer.create_server ()
        self.gen_domain_name (server.server_address)
        server_rules = self.parse_files ()
        server.server_conf (self.file_list, server_rules)
        HTTPServer.spawn_server (server)

    def init_FTP_server (self):
       # FTPServer.init_server ()
        self.server = FTP.FTPd ()
        self.server.start ()
        self.gen_domain_name ([self.server.host, self.server.port])
        server_rules = self.parse_files ()
        FTPServer.mk_file_sys (self.file_list)

    def gen_domain_name (self, addr):
        port = addr[1]
        domain_name = addr[0]
        self.domain = domain_name + ":" + str (port) + "/"

    def stop_server (self):
        func = "stop_" + self.server_type + "_server"
        assert hasattr (self, func)
        getattr (self, func) ()

    """ Send a HTTP QUIT Request to stop the Server """

    def stop_HTTP_server (self):
        conn = http.client.HTTPConnection (self.domain.strip ('/'))
        conn.request ("QUIT", "/")
        self.fileSys = HTTPServer.ret_fileSys()
        conn.getresponse ()

    def stop_FTP_server (self):
        self.server.stop ()
        self.fileSys = FTPServer.filesys ()

    def append_downloads (self, filename, User=None, Pass=None):
        prep = "" if User is None else User + ":" + Pass + "@"
        URL = prep + self.domain + filename + " "
        URL = self.server_type.lower () + "://" + URL
        self.download_list += URL

    def parse_files (self):
        self.file_list = dict ()
        server_rules = dict ()
        for file_node in self.Root.findall ('File'):
            try:
                metadata = file_node.find ('Meta')
                self.filename = metadata.get ('name')
                no_download = metadata.get ('no-download')
                toDownload = True if no_download is None else False
                content_node = file_node.find ('Content')
                if content_node is not None:
                    self.file_list[self.filename] = content_node.text
                else:
                    self.file_list[self.filename] = ""
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

    class Auth:

        def __init__ (self, a_type, a_user, a_pass):
            self.auth_type = a_type
            self.auth_user = a_user
            self.auth_pass = a_pass

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
        header = self.special_comm.find ('Name').text
        value = self.special_comm.find ('Value').text
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

    def get_auth (self):
        auth_type = self.special_comm.find ('Type').text
        auth_user = self.special_comm.find ('Username').text
        auth_pass = self.special_comm.find ('Password').text
        auth_obj = self.Auth (auth_type, auth_user, auth_pass)
        if self.special_comm.find ('InURL') is not None:
            self.append_downloads (
                self.filename, User=auth_user, Pass=auth_pass)
        return [("Auth", auth_obj)]

    def get_expect_header (self):
        header = self.special_comm.find ('Name').text
        value = self.special_comm.find ('Value').text
        header_obj = self.Cust_Header (header, value)
        return [("Expect Header", header_obj)]

    def parse_server_rules (self, file_node):
        special_conf = defaultdict (list)
        self.meth_files = ""
        commands_list = {
            "Redirect": self.get_redir,
            "Continue": self.set_cont,
            "ContentDisposition": self.get_cont_disp,
            "Header": self.get_header,
            "Cookie": self.get_cookie,
            "Response": self.get_response,
            "Auth": self.get_auth,
            "Expect Header": self.get_expect_header
        }
        for self.special_comm in file_node.findall ('ServerRule'):
            command = self.special_comm.get ('command')
            try:
                rule_obj = commands_list.get(command) ()
            except TypeError as ae:
                e_str = "Config details for Rule: " + command + " do not exist"
                raise TestFailed (e_str)
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
        expected_ret_code = int (self.resultsNode.find ('ReturnCode').text)
        if retCode != expected_ret_code:
            printer ("RED", "Expected Exit Code: " + str (expected_ret_code))
            printer ("RED", "Actual Exit Code:   " + str (retCode))
            self._test_cleanup ()
            raise TestFailed ("")

    def _gen_expected_files (self):
        expected_files = dict ()
        for expectedFile in self.resultsNode.findall ('File'):
            orig_file = expectedFile.get ('orig')
            orig_name = expectedFile.text if orig_file is None else orig_file
            expected_files[expectedFile.text] = orig_name
        return expected_files

    def test_downloaded_files (self):
        expected_files = self._gen_expected_files()
        # Go through all files in PWD, which is the test directory
        for parent, dirs, files in os.walk ("."):
            for filename in files:
                if parent != ".":
                    continue
                if filename in expected_files:
                    file_handler = open (filename, "r")
                    file_content = file_handler.read()
                    real_contents = self.fileSys.get (expected_files[filename])
                    if real_contents != file_content:
                        e_str = "Contents of " + filename + " do not match"
                        printer ("RED", e_str)
                        for line in unified_diff (real_contents, file_content,
                                                  fromfile="Original", tofile="Actual"):
                            sys.stderr.write (line)
                        print()  # Print empty line for formatting purposes
                        file_handler.close ()
                        self._test_cleanup ()
                        raise TestFailed ("")
                    del expected_files[filename]
                else:
                    printer ("RED", "Extra files downloaded by Wget.")
                    self._test_cleanup ()
                    raise TestFailed ("")
            if expected_files:
                missing = str (list (expected_files.keys ())).strip ("[']")
                printer ("RED", "Not all expected files were downloaded.")
                printer ("RED", "Missing files: " + missing)
                self._test_cleanup ()
                raise TestFailed ("")


# vim: set ts=8 sw=3 sts=4 tw=0 et :
