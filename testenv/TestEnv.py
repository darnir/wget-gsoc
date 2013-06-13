import HTTPServer
import http.client
import os
import shutil
import difflib
import sys
from ColourTerm import printer
from xml.etree.ElementTree import parse
from multiprocessing import Process

testdir = ""

def start_server (inputFile):
    server_process = Process(target=HTTPServer.initServer, args=(inputFile, ))
    server_process.start()

# Send a HTTP QUIT Request to stop the Server
def stop_server ():
    conn = http.client.HTTPConnection("localhost:8090")
    conn.request("QUIT", "/")
    conn.getresponse()

class TestFailed(Exception):
    pass

class Test:
    TestFailed = TestFailed
    def __init__(self, TestFile):
        TestTree2 = parse(TestFile)
        self.Root = TestTree2.getroot()
        self.testDir = TestFile + "-test"
        self.resultsNode = self.Root.find('ExpectedResults')
        try:
            os.mkdir(self.testDir)
        except FileExistsError as ae:
            shutil.rmtree(self.testDir)
            os.mkdir(self.testDir)
        os.chdir(self.testDir)
    def gen_file_list(self):
        self.download_list = ""
        self.file_list = dict()
        for file_element in self.Root.findall('InputFile'):
            self.file_list[file_element.get('name')] = file_element.text
            if file_element.get('download') == 'False':
                continue
            self.download_list = self.download_list + "localhost:8090/" + file_element.get('name') + " "
        return self.file_list
    def get_cmd_line(self, WgetPath):
        cmd_line = WgetPath + " "
        for parameter in self.Root.findall('Option'):
            cmd_line += parameter.text + " "
        cmd_line += self.download_list
        return cmd_line
    def _test_cleanup(self):
        os.chdir("..")
        shutil.rmtree(self.testDir)
    def endTest(self):
        self._test_cleanup()
    def test_return_code(self, retCode):
        expected_return_code = int(self.resultsNode.find('ReturnCode').text)
        if retCode != expected_return_code:
            printer ("RED", "Expected Exit Code: " + str(expected_return_code))
            printer ("RED", "Actual Exit Code:   " + str(retCode))
            self._test_cleanup()
            raise TestFailed()
    def _gen_expected_files(self):
        expected_files = dict()
        for expectedFile in self.resultsNode.findall('File'):
            origName = expectedFile.get('orig') if expectedFile.get('orig') else expectedFile.text
            expected_files[expectedFile.text] = origName
        return expected_files
    def _test_extra_files(self):
        for parent, dirs, files in os.walk("."):
            if files:
                printer ("RED", "Extra files downloaded by Wget")
                printer ("RED", str(files).strip("[']"))
                self._test_cleanup()
                raise TestFailed()
    def test_downloaded_files(self):
        expected_files = self._gen_expected_files()
        for filename in expected_files:
            try:
                FileHandler = open(filename, "r")
            except IOError as ae:
                printer("RED", str(ae))
                self._test_cleanup()
                raise TestFailed()
            FileContent = FileHandler.read()
            if self.file_list.get(expected_files[filename]) != FileContent:
                printer("RED", "Contents of " + filename + " do not match")
                for line in difflib.unified_diff(self.file_list.get(expected_files[filename]),
                                                FileContent, fromfile="Original", tofile="Actual"):
                    sys.stdout.write(line)
                print("")
                FileHandler.close()
                self._test_cleanup()
                raise TestFailed()
            FileHandler.close()
            os.remove(filename)
        self._test_extra_files()
