#!/usr/bin/env python

import HTTPServer
import http.client
from multiprocessing import Process
from time import sleep

def stop_server ():
    """send QUIT request to http server running on localhost:<port>"""
    conn = http.client.HTTPConnection("localhost:8090")
    conn.request("QUIT", "/")
    conn.getresponse()

server_process = Process(target=HTTPServer.initServer, args=())
server_process.start()

# This sleep statement will be removed later as automation is added
sleep (10)

stop_server()

