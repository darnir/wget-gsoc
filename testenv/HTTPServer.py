#!/usr/bin/env python

#from threading import Thread
#from socketserver import ThreadingMixIn

from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class __Handler(BaseHTTPRequestHandler):

    # The do_* methods define how each of the HTTP Request Methods are handled by this server.

    def do_GET(self):
        rootdir = '.'
        filepath = rootdir + self.path
        try:
            f = open(filepath)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", os.path.getsize(filepath))
#           self.send_header("Location", "main.html")
            self.end_headers()
            self.wfile.write(bytes(f.read(), 'utf-8'))
        except IOError as ae:
            self.send_error(404, 'Not Found')
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

#class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
#    pass

def __serve_on_port(port):
    server = HTTPServer(("localhost", port), __Handler)
    server.serve_forever()

# The public interface to this Module. Please do not change interface unless absolutely required.
def initServer():
    __serve_on_port(8090)

#Thread(target=serve_on_port, args=[1111]).start()
