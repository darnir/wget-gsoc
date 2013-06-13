import HTTPServer
import http.client
import os
import shutil
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

def init_test_env (test):
    TestTree = parse(test)
    Root = TestTree.getroot()
    global testdir
    testdir = test+"-test"
    try:
        os.mkdir(testdir)
    except FileExistsError as ae:
        shutil.rmtree(testdir)
        os.mkdir(testdir)
    os.chdir(testdir)
    return Root

def __test_cleanup():
    os.chdir("..")
    shutil.rmtree(testdir)

def exit_test(retCode):
    if retCode > 24:
        printer ("RED", "Test Failed.")
    __test_cleanup()
    exit(retCode)
