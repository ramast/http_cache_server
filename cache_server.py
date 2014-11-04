#!/usr/bin/env python3
# Copytights Ramast (M. Magdy) 2013
# Code provided under GPLv2 license

import http.server
import ssl
import os
import urllib3
import re
import json
import threading
import signal
import socket
import socketserver
import time
import sys

HOST_NAME = '127.0.0.2'
ALLOWED_HEADERS = {"Age", "Expires", "Last-Modified", "Cache-Control", "Content-Type"}
DEBUG = False


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Make my http server multithreaded"""
    pass


class HttpCacheManager(http.server.BaseHTTPRequestHandler):
    http = urllib3.PoolManager()
    resolve_regex = re.compile("has address ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)")
    _dns_cache = {}

    @classmethod
    def resolve_hostname(cls, hostname):
        print("Resolving host %s" % hostname)
        #Have I resolved this domain before?
        if hostname in cls._dns_cache:
            if cls._dns_cache[hostname] == "LOCK":
                #Wait 5 seconds then try again
                time.sleep(5)
                return cls.resolve_hostname(hostname)
            return cls._dns_cache[hostname]
        #Lock the entry to preven other threads from looking up same DNS name
        cls._dns_cache[hostname] = "LOCK"
        ips = []
        res_re = cls.resolve_regex
        with os.popen("host %s" % hostname) as f:
            for line in f:
                ip = res_re.search(line)
                if not ip:
                    continue
                ips.append(ip.group(1))
                if len(ips) > 3:
                    break
        #Cache the result if its valid
        if ips:
            cls._dns_cache[hostname] = ips
            return ips
        del cls._dns_cache[hostname]
        return False

    def give_error(self, message):
        self.send_response(404)
        self.end_headers()
        self.wfile.write("ERROR: %s"%message)
        return

    def do_GET(self):
        if self.path == "/favicon.ico":
            return self.give_error("No fav")
        if "Referer" in self.headers:
            print(self.headers["Referer"], end=" => ")
        print(self.headers["HOST"])
        if "If_Modified_Since" in self.headers:
            #Send Not modified response
            self.send_response(304)
            self.end_headers()
            return

        host_name, *_ = self.headers["HOST"].split(":")
        file_path = os.path.join(self.cache_dir, host_name, self.path[1:])
        file_name = os.path.join(file_path, "index")
        if isinstance(self.connection, ssl.SSLSocket):
            protocol = "https"
        else:
            protocol = "http"
        if not os.path.exists(file_name):
            response = None
            #Find the ip of the host
            ips = self.resolve_hostname(host_name)
            if ips == False:
                return self.give_error("Couldn't resolve %s"%host_name)
            for ip in ips:
                url = "%s://%s%s" % (protocol, ip, self.path)
                try:
                    response = self.http.request("GET", url, None, dict(self.headers), timeout=5)
                    if response.status != 200:
                        #Failure? send status code only and return
                        self.send_response(response.status)
                        self.end_headers()
                        self.wfile.write(response.data)
                        return
                except urllib3.exceptions.HTTPError as e:
                    print("Failed to get %s : Error %s"%(url, str(e.args)))
                    #Try next IP
                    continue
                #If everything is alright get out of the loop
                break
            if not response:
                self.give_error("Failed to get %s : Response was empty"%url)
            #save the file
            os.system("mkdir -p '%s'" % file_path)
            content = response.data
            with open(file_name, "wb") as f:
                f.write(content)
            #And its headers
            f = open(file_name + ".headers", "wb")
            headers = json.dumps(dict(response.headers)).encode("ascii")
            f.write(headers)
            f.close()

        #Read headers
        f = open(file_name + ".headers", "r", encoding="ascii")
        headers = json.loads(f.read())
        f.close()
        #Send the headers
        self.send_response(200)
        for key, value in headers.items():
            if key in ALLOWED_HEADERS:
                self.send_header(key, value)
        self.end_headers()
        #Send content
        try:
            with open(file_name, "rb") as f:
                while True:
                    chunk = f.read(10240)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except socket.error:
            print("Browser closed connection: %s" % file_path)

    @classmethod
    def start(cls, protocol, port):
        global cert_file
        if DEBUG:
            server_class = http.server.HTTPServer
        else:
            server_class = ThreadedHTTPServer
        HttpCacheManager.protocol = protocol
        httpd = server_class((HOST_NAME, port), HttpCacheManager)
        if protocol == "https":
            #TODO: use a better way to specify the pem file
            httpd.socket = ssl.wrap_socket(httpd.socket,
                                           certfile=cert_file,
                                           server_side=True)
        cls.cache_dir = cache_dir
        print(time.asctime(), "Server Starts - %s:%s" % (HOST_NAME, port))
        httpd.serve_forever()
        httpd.server_close()
        print(time.asctime(), "Server Stops - %s:%s" % (HOST_NAME, port))


if __name__ == '__main__':

    def terminate(*args, **kwargs):
        global t1, t2
        t1._stop()
        t2._stop()

    #cache dir
    cache_dir = "cache"
    if len(sys.argv) == 3:
        cache_dir = sys.argv[1]
        cert_file = sys.argv[2]
    # Handle -h and --help arguments properly
    if len(sys.argv) != 3 or cache_dir == "-h" or cache_dir == "--help":
        print("Usage %s cache_dir cert_file"%sys.argv[0])
        exit(1)

    if DEBUG:
        HttpCacheManager.start("https", 9000)
    else:
        t1 = threading.Thread(target=HttpCacheManager.start, args=("https", 443))
        t1.start()
        t2 = threading.Thread(target=HttpCacheManager.start, args=("http", 80))
        t2.start()
        signal.signal(signal.SIGTERM, terminate)
        signal.signal(signal.SIGINT, terminate)
