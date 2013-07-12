from multiprocessing import Process, Queue
from http.server import HTTPServer, BaseHTTPRequestHandler
from base64 import b64encode
from random import random
import os
import re


class InvalidRangeHeader (Exception):

    """ Create an Exception for handling of invalid Range Headers. """
    # Maybe: This exception should be generalized to handle other issues too.

    def __init__ (self, err_message):
        self.err_message = err_message


class StoppableHTTPServer (HTTPServer):

    """ Define methods for configuring the Server. """

    def server_conf (self, filelist, conf_dict):
        """ Set Server Rules and File System for this instance.

        This method should be called before the Server is forked into a new
        process. This is because of how the system-level fork() call works.

        """
        global server_configs
        server_configs = conf_dict
        global fileSys
        fileSys = filelist

    def serve_forever (self, q):
        """ Override method allowing for programmatical shutdown process. """
        global queue
        queue = q
        self.stop = False
        while not self.stop:
            self.handle_request ()


class WgetHTTPRequestHandler (BaseHTTPRequestHandler):

    """ Define methods for handling Test Checks. """

    # List of Checks that are run on the Server-side.
    tests = [
        "expect_headers",
        "is_auth",
        "custom_response",
        "test_cookies"
    ]

    def test_cookies (self):
        cookie_recd = self.headers.get ('Cookie')
        cookies = self.get_rule_list ('Cookie')
        cookie_exp = cookies[0].cookie_value if cookies else None
        if cookie_exp == cookie_recd:
            return True
        else:
            self.send_response (400, "Cookie Mismatch")
            self.finish_headers ()
            return False

    def get_rule_list (self, name):
        r_list = self.rules.get (name) if name in self.rules else list ()
        return r_list

    def do_QUIT (self):
        queue.put (fileSys)
        self.send_response (200)
        self.end_headers ()
        self.server.stop = True


class __Handler (WgetHTTPRequestHandler):

    """ Define Handler Methods for different Requests. """

    InvalidRangeHeader = InvalidRangeHeader
    protocol_version = 'HTTP/1.1'

    """ Define functions for various HTTP Requests. """

    def do_HEAD (self):
        self.send_head ()

    def do_GET (self):
        content, start = self.send_head ()
        if content:
            if start is None:
                self.wfile.write (content.encode ('utf-8'))
            else:
                self.wfile.write (content.encode ('utf-8')[start:])

    def do_POST (self):
        path = self.path[1:]
        self.rules = server_configs.get (path)
        if not self.custom_response ():
            return (None, None)
        if path in fileSys:
            body_data = self.get_body_data ()
            self.send_response (200)
            self.send_header ("Content-type", "text/plain")
            content = fileSys.pop (path) + "\n" + body_data
            total_length = len (content)
            fileSys[path] = content
            self.send_header ("Content-Length", total_length)
            self.finish_headers ()
            try:
                self.wfile.write (content.encode ('utf-8'))
            except Exception:
                pass
        else:
            self.send_put (path)

    def do_PUT (self):
        path = self.path[1:]
        self.rules = server_configs.get (path)
        if not self.custom_response ():
            return (None, None)
        fileSys.pop (path, None)
        self.send_put (path)

    """ End of HTTP Request Method Handlers. """

    """ Helper functions for the Handlers. """

    def parse_range_header (self, header_line, length):
        if header_line is None:
            return None
        if not header_line.startswith ("bytes="):
            raise InvalidRangeHeader ("Cannot parse header Range: %s" %
                                     (header_line))
        regex = re.match (r"^bytes=(\d*)\-$", header_line)
        range_start = int (regex.group (1))
        if range_start >= length:
            raise InvalidRangeHeader ("Range Overflow")
        return range_start

    def get_body_data (self):
        cLength_header = self.headers.get ("Content-Length")
        cLength = int (cLength_header) if cLength_header is not None else 0
        body_data = self.rfile.read (cLength).decode ('utf-8')
        return body_data

    def send_put (self, path):
        body_data = self.get_body_data ()
        self.send_response (201)
        fileSys[path] = body_data
        self.send_header ("Content-type", "text/plain")
        self.send_header ("Content-Length", len (body_data))
        self.finish_headers ()
        try:
            self.wfile.write (body_data.encode ('utf-8'))
        except Exception:
            pass

    def send_cust_headers (self):
        header_obj = self.get_rule_list ('Header')
        for header in header_obj:
            self.send_header (header.header_name, header.header_value)

    def finish_headers (self):
        self.send_cust_headers ()
        self.end_headers ()

    def custom_response (self):
        codes = self.get_rule_list ('Response')
        if codes:
            self.send_response (codes[0].response_code)
            self.finish_headers ()
            return False
        else:
            return True

    def base64 (self, data):
        string = b64encode (data.encode ('utf-8'))
        return string.decode ('utf-8')

    def is_auth (self):
        auth = self.get_rule_list ('Auth')
        if auth:
            auth_type = auth[0].auth_type
            auth_header = self.headers.get ("Authorization")
            if auth_type == "Basic" and auth_header is None:
                self.send_response (401)
                self.send_header ("WWW-Authenticate", 'Basic realm="Test"')
                self.end_headers ()
                return False
            elif auth_type == "Digest" and auth_header is None:
                self.send_response (401)
                nonce = self.base64 (str (random ()))
                opaque = self.base64 (str (random ()))
                digest_string = "Digest "
                digest_string += 'realm="Test", '
                digest_string += 'nonce="%s", ' % nonce
                digest_string += 'opaque="%s", ' % opaque
                self.send_header ("WWW-Authenticate", digest_string)
                self.end_headers ()
                return False
            else:
                user = auth[0].auth_user
                passw = auth[0].auth_pass
                auth_string = user + ":" + passw
                auth_enc = self.base64 (auth_string)
                auth_header = self.headers.get ("Authorization")
                auth_header = auth_header.replace ("Basic ", "", 1)
                if auth_header == auth_enc:
                    return True
                else:
                    self.send_response (401)
                    self.send_header ("WWW-Authenticate", 'Basic realm="Test"')
                    self.end_headers ()
                    return False
        else:
            return True

    def expect_headers (self):
        header = self.get_rule_list ('Expect Header')
        if header:
            for header_line in header:
                header_re = self.headers.get (header_line.header_name)
                if header_re is None or header_re != header_line.header_value:
                    self.send_error (400, 'Expected Header not Found')
                    self.end_headers ()
                    return False
        return True

    def send_head (self):
        """ Common code for GET and HEAD Commands.
        This method is overriden to use the fileSys dict.
        """
        path = self.path[1:]
        self.rules = server_configs.get (path)

        testPassed = True
        for check in self.tests:
            if testPassed is True:
                assert hasattr (self, check)
                testPassed = getattr (self, check) ()
            else:
                return (None, None)

        if path in fileSys:
            content = fileSys.get (path)
            content_length = len (content)
            try:
                self.range_begin = self.parse_range_header (
                    self.headers.get ("Range"), content_length)
            except InvalidRangeHeader as ae:
                # self.log_error("%s", ae.err_message)
                if ae.err_message == "Range Overflow":
                    self.send_response (416)
                    self.finish_headers ()
                    return (None, None)
                else:
                    self.range_begin = None
            if self.range_begin is None:
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
            self.finish_headers ()
            return (content, self.range_begin)
        else:
            self.send_error (404, "Not Found")
            return (None, None)


def create_server ():
    server = StoppableHTTPServer (("localhost", 0), __Handler)
    return server


def spawn_server (server):
    global q
    q = Queue()
    server_process = Process (target=server.serve_forever, args=(q,))
    server_process.start ()


def ret_fileSys ():
    return (q.get (True))

# vim: set ts=8 sts=4 sw=3 tw=0 et :
