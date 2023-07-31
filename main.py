#!/usr/bin/env python3
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import time

from gather_data_legacy import parse

from gather_data import parse_all
from convert_data import convert
from build_homeassistant_sensors import build_homeassistant_rest_sensor_template, build_home_assistant_data_response

hostName = ""
serverPort = 8080
serverAddr = None
if os.environ.get("USE_HOSTNAME","").lower() == "true":
    import socket
    serverAddr = f"http://{socket.gethostname()}:{serverPort}"

class LegacyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.endswith("/mappings"):
            response = parse(mapping=True)
        else:
            response = parse()

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(response, "utf-8"))


cached_value = None
cached_datetime = 0
cache_timeout = 60

def get_raw():
    global cached_value
    global cached_datetime
    global cache_timeout
    current_time = time.time()
    if cached_value is None or (current_time - cached_datetime) > cache_timeout:
        cached_value = parse_all()
        cached_datetime = current_time
    return cached_value

class Server(BaseHTTPRequestHandler):
    def _build_response(self, body, is_json=True):
        if body == False:
            self.send_response(404)
            self.end_headers()
            return
        
        self.send_response(200)
        content_type = "application/json"
        if is_json and not isinstance(body, str):
            body = json.dumps(body)
        if not is_json:
            content_type = "text/plain"
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(bytes(body, "utf-8"))

    
    def do_GET(self):
        if self.path == "/template":
            global serverAddr
            _serverAddr = serverAddr
            if not _serverAddr:
                _serverAddr = f"http://{self.headers['HOST']}"
            self._build_response(build_homeassistant_rest_sensor_template(convert(get_raw()), _serverAddr), is_json=False)
        elif self.path == "/raw":
            self._build_response(get_raw())
        elif self.path == "/ha":
            self._build_response(build_home_assistant_data_response(convert(get_raw())))
        elif self.path == "/":
            self._build_response(convert(get_raw()))
        elif self.path == "/healthcheck":
            self._build_response({"healthcheck": "okay"})
        else:
            self._build_response(False)


if __name__ == "__main__":
    mode = os.environ.get("MODE", None)
    if mode:
        if mode == "SERVER":
            webServer = HTTPServer((hostName, serverPort), LegacyServer)
            print("Server started http://%s:%s" % (hostName, serverPort))

            try:
                webServer.serve_forever()
            except KeyboardInterrupt:
                pass
            webServer.server_close()
            print("Server stopped.")
        elif mode.lower() == "server_v2":
            webServer = HTTPServer((hostName, serverPort), Server)
            print("Server started http://%s:%s" % (hostName, serverPort))

            try:
                webServer.serve_forever()
            except KeyboardInterrupt:
                pass
            webServer.server_close()
            print("Server stopped.")
        elif mode == "MAPPING":
            print(parse(mapping=True))
    else:
        print(parse())