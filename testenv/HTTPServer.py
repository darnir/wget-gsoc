#!/usr/bin/env python
from threading import Thread
from socketserver import ThreadingMixIn
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        rootdir = '/'
        try:
            f = open(rootdir + self.path)

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.send_header("Length", "400")
#           self.send_header("Location", "main.html")
            self.end_headers()
            self.wfile.write(bytes(f.read(), 'utf-8'))
        except IOError as ae:
            self.send_error(404, 'File Not Found')
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

def serve_on_port(port):
    server = ThreadingHTTPServer(("localhost", port), Handler)
    server.serve_forever()

Thread(target=serve_on_port, args=[1111]).start()
serve_on_port(2222)
