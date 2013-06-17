#!/usr/bin/env python

#from threading import Thread
#from socketserver import ThreadingMixIn
from multiprocessing import Process
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

fileSys = dict()

## Custom Class Definitions. These extend the standard classes
# so as to add support for stopping them programmatically.

class StoppableHTTPRequestHandler (BaseHTTPRequestHandler):

    protocol_version = 'HTTP/1.1'
    def do_QUIT (self):
        self.send_response(200)
        self.end_headers()
        self.server.stop = True

class StoppableHTTPServer (HTTPServer):

    def serve_forever (self):
        self.stop = False
        while not self.stop:
            self.handle_request()

## End Custom Class Declarations

class __Handler(StoppableHTTPRequestHandler):

    # The do_* methods define how each of the HTTP Request Methods are handled by this server.

    def do_HEAD(self):
        self.send_head()

    def do_GET(self):
        content = self.send_head()
        if content:
            self.wfile.write(content.encode('utf-8'))

    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def send_head(self):
        """ Common code for GET and HEAD Commands.
        This method is overriden to use the fileSys dict.
        """
        path = self.path[1:]
        if path in fileSys:
            content = fileSys.get(path)
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            return content
        else:
            self.send_error(404, "Not Found")
            return None

#class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
#    pass

def create_server ():
    server = StoppableHTTPServer (("localhost", 0), __Handler)
    return server

def spawn_server (server):
    server_process = Process (target=server.serve_forever)
    server_process.start()

def mk_file_sys (inputFile):
    global fileSys
    fileSys = inputFile
#Thread(target=serve_on_port, args=[1111]).start()
