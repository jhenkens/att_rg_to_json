#!/usr/bin/env python3
from bs4 import BeautifulSoup
import json
import requests
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEM_URL = 'http://192.168.1.254/cgi-bin/broadbandstatistics.ha'
def parse():
    page = requests.get(MODEM_URL)

    soup = BeautifulSoup(page.content, 'html.parser')
    line_data = [
        "LineState",
        "DSSync",
        "USSync",
        "DSMax",
        "USMax",
        "Modulation",
        "DataPath",
    ]
    bi_dir_data = [
        "SN",
        "Attenuation",
        "Power",
        "Seconds",
        "LOS",
        "LOF",
        "FEC",
        "CRC",
    ]
    global_data = [
        "Transmit Packets",
        "Transmit Errors",
        "Transmit Discards",
        "Transmit Bytes",
        "Receive Packets",
        "Receive Errors",
        "Receive Discards",
        "Receive Bytes",
        "PTM Receive PDUs",
        "Broadband Connection",
        "Broadband Network Type",
        "MTU",
    ]

    time_data = [
        "Severely Errored Seconds (SESL)",
        "Unavailable Seconds (UASL)",
        "DSL Initialization Timeouts",
    ]
    time_keys = []
    table_keys = []
    for l in range(1, 3):
        for d in line_data:
            table_keys.append("Line" + str(l) + " " + d)
        for d in ["DS", "US"]:
            for k in bi_dir_data:
                table_keys.append("Line" + str(l) + " " + k + " " + d + str(l))
        for t in time_data:
            time_keys.append(t + " Line " + str(l))

    results = {}
    for key in global_data:
        key_results = soup.find("th", text=key).parent.find('td')
        results[key] = key_results.text.strip()
    for key in table_keys:
        key_results = soup.find("td", {"headers": key})
        results[key] = key_results.text.strip()

    timed_table = soup.find('table', {"summary": "Table of timed statistics"})
    for key in time_keys:
        # line endings are weird for time_keys, do it inefficiently
        key_results = [f for f in timed_table.findAll("td") if f.text and key in f.text][0]
        key_result = key_results.parent.findAll('td')[-1]
        dest_key = re.sub(r"\([A-Z]+\) ", "", key)
        results[dest_key] = key_result.text.strip()

    def normalize(d):
        # Replace spaces w/ underscores, lowercase dictionary keys and strip/convert values to integers
        def normalize_key(k):
            k = k.replace(" ", "_").lower()
            k = re.sub(r'(.*)_line_(\d)',r'line\2_\1',k)
            k = re.sub(r'([du]s)\d$',r'\1',k)
            return k
        def normalize_value(v):
            try:
                return float(v)
            except ValueError:
                return v
            
        return {normalize_key(k): normalize_value(v) for k, v in d.items()}


    results = normalize(results)

    results = {k: v for k, v in results.items() if isinstance(v, float)}

    return json.dumps(results, indent=2, sort_keys=True)
    
hostName = ''
serverPort = 8080

class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(parse(), "utf-8"))

if __name__ == "__main__":        
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
    

