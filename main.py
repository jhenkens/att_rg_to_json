#!/usr/bin/env python3
import sys
from bs4 import BeautifulSoup
import json
import requests
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEM_URL = 'http://192.168.1.254/cgi-bin/broadbandstatistics.ha'


def parse(mappings=False):
    page = requests.get(MODEM_URL)

    soup = BeautifulSoup(page.content, 'html.parser')
    global_data = {
        "Summary of the most important WAN information": [
            "Broadband Connection",
            "Broadband Network Type",
            "MTU",
        ],
        "IPv4 Table": [
            "Transmit Packets",
            "Transmit Errors",
            "Transmit Discards",
            "Transmit Bytes",
            "Receive Packets",
            "Receive Errors",
            "Receive Discards",
            "Receive Bytes",
            "PTM Receive PDUs",
        ]
    }
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
    time_data = [
        "Severely Errored Seconds (SESL)",
        "Unavailable Seconds (UASL)",
        "DSL Initialization Timeouts",
    ]
    time_keys = {}
    table_keys = {}
    results = {}
    descriptions = {}

    def normalize_key(k):
        k = k.replace(" ", "_").lower()
        k = re.sub(r'\([A-Za-z]+\)$','',k)
        return k.strip('_')
    
    def lookup(key):
        value_element = soup.find("td", {"headers": key})
        header_element = value_element.parent.find('th')
        
        description = f'Line {l} {header_element.text.strip()}'
        key = normalize_key(description)
        
        results[key] = value_element.text.strip()
        descriptions[key] = description
        
    
    timed_table = soup.find('table', {"summary": "Table of timed statistics"}).find_all("td")
    for l in range(1, 3):
        for d in line_data:
            lookup(f"Line{l} {d}")
        for d in ["DS", "US"]:
            for k in bi_dir_data:
                lookup(f"Line{l} {k} {d}{l}")
        for t in time_data:
            lookup_key = f"{t} Line {l}"
            # line endings are weird for time_keys, do it inefficiently
            header = [f for f in timed_table if f.text and lookup_key in f.text][0]
            value_element = header.parent.findAll('td')[-1] # total
            description = re.sub(r"\([A-Z]+\)", "", t).strip()
            description = f'Line {l} {description}'
            
            key = normalize_key(description)
            results[key] = value_element.text.strip()
            descriptions[key] = description
            
    for table, keys in global_data.items():
        table = soup.find('table', {"summary": table})
        for key in keys:
            value_element = table.find("th", text=key).parent.find('td')
            description = key

            key = normalize_key(description)
            results[key] = value_element.text.strip()
            descriptions[key] = description

    def normalize_value(v):
        try:
            return float(v)
        except ValueError:
            return v

    results = {k: normalize_value(v) for k,v in results.items()}

    if mappings:
        return json.dumps(descriptions, indent=2, sort_keys=True)
    else:
        return json.dumps(results, indent=2, sort_keys=True)


hostName = ''
serverPort = 8080


class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        response = parse()
        if self.path.endswith('/mappings'):
            response = parse(mappings=True)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(response, "utf-8"))


if __name__ == "__main__":
    webServer = HTTPServer((hostName, serverPort), MyServer)
    print("Server started http://%s:%s" % (hostName, serverPort))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")
