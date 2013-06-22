#from threading import Thread
#from socketserver import ThreadingMixIn
from multiprocessing import Process
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import re

## Custom Class Definitions. These extend the standard classes
# so as to add support for stopping them programmatically.


class StoppableHTTPRequestHandler (BaseHTTPRequestHandler):

   protocol_version = 'HTTP/1.1'
   def do_QUIT (self):
      self.send_response (200)
      self.end_headers ()
      self.server.stop = True

class StoppableHTTPServer (HTTPServer):

   def server_conf (self, conf_dict):
      global server_configs
      server_configs = conf_dict

   def serve_forever (self):
      self.stop = False
      while not self.stop:
         self.handle_request ()

class InvalidRangeHeader (Exception):
   def __init__ (self, err_message):
      self.err_message = err_message

## End Custom Class Declarations

class __Handler (StoppableHTTPRequestHandler):
   InvalidRangeHeader = InvalidRangeHeader
   # The do_* methods define how each of the HTTP Request Methods are handled by this server.

   def parse_range_header (self, header_line, length):
      if header_line is None or header_line == "":
         return None
      if not header_line.startswith ("bytes="):
         raise InvalidRangeHeader ("Cannot parse header Range: %s" %(header_line))
      regex = re.match (r"^bytes=(\d*)\-$", header_line)
      range_start = int (regex.group (1))
      if range_start > length:
         raise InvalidRangeHeader ("Range overflow")
      return range_start

   def do_HEAD (self):
      self.send_head ()

   def do_GET (self):
      content, start = self.send_head ()
      if content:
         if start == None:
            self.wfile.write (content.encode ('utf-8'))
         else:
            self.wfile.write (content.encode ('utf-8')[start:])

   def do_POST (self):
      path = self.path[1:]
      if path in redir_list:
         self.send_redirection (redir_list.get (path))
      else:
         self.send_response (200)
         self.send_header ("Content-type", "text/plain")
         self.end_headers ()

   def handle_redirects (self, path):
      if "Redirect" in server_configs:
         redir_list = server_configs.get ('Redirect')
         for obj in redir_list:
            if path == obj.from_uri:
               self.send_response (int (obj.stat_code))
               self.send_header ("Location", obj.to_uri)
               self.end_headers()
               return True
      else:
         return False

   def send_content_disposition_header (self, path):
      if "ContentDisp" in server_configs:
         contentdisp = server_configs.get ('ContentDisp')
         for obj in contentdisp:
            if path == obj.cd_url:
               self.send_header ("Content-Disposition", 'Attachment; filename=%s' %(obj.cd_name))

   def send_head (self):
      """ Common code for GET and HEAD Commands.
      This method is overriden to use the fileSys dict.
      """
      path = self.path[1:]

      if self.handle_redirects (path) is True:
         return (None, None)

      if path in fileSys:
         content = fileSys.get (path)
         content_length = len (content)
         try:
            self.range_begin = self.parse_range_header (self.headers.get ("Range"), \
                                                                     content_length)
         except InvalidRangeHeader as ae:
            #self.log_error("%s", ae.err_message)
            if ae.err_message == "Range Overflow":
               self.send_response (416)
               self.end_headers ()
               return (None, None)
            else:
               self.range_begin = None
         if self.range_begin == None:
            self.send_response (200)
         else:
            self.send_response (206)
            self.send_header ("Accept-Ranges", "bytes")
            self.send_header ("Content-Range",
                              "bytes %d-%d/%d" % (self.range_begin,
                                                  content_length - 1,
                                                  content_length))
            content_length -= self.range_begin
         self.send_header ("Content-type", "text/plain")
         self.send_header ("Content-Length", content_length)
         self.send_content_disposition_header (path)
         self.end_headers ()
         return (content, self.range_begin)
      else:
         self.send_error (404, "Not Found")
         return (None, None)

#class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
#   pass

def create_server ():
   server = StoppableHTTPServer (("localhost", 0), __Handler)
   return server

def spawn_server (server):
   server_process = Process (target=server.serve_forever)
   server_process.start ()

def mk_file_sys (inputFile):
   global fileSys
   fileSys = inputFile

#Thread(target=serve_on_port, args=[1111]).start()

# vim: set ts=8 sts=3 sw=3 tw=0 et :
