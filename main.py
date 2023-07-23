#!/usr/bin/env python3
from bs4 import BeautifulSoup
import sys, json, requests, re, os
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEM_URL = "http://192.168.1.254/cgi-bin/broadbandstatistics.ha"


def parse(mapping=False):
    page = requests.get(MODEM_URL)

    soup = BeautifulSoup(page.content, "html.parser")
    global_data = {
        "Summary": {
            "table_summaries": ["Summary of the most important WAN information"],
            "keys": [
                "Broadband Connection",
                "Broadband Network Type",
                "MTU",
            ],
        },
        "IPv4": {
            "table_summaries": ["IPv4 Table", "Ethernet IPv4 Statistics Table"],
            "keys": [
                "Transmit Packets",
                "Transmit Errors",
                "Transmit Discards",
                "Transmit Bytes",
                "Receive Packets",
                "Receive Errors",
                "Receive Discards",
                "Receive Bytes",
                "PTM Receive PDUs",
            ],
        },
        "GPon": {
            "table_summaries": ["GPON Status Table"],
            "keys": [
                "PON Link Status",
                "UNI Status",
            ],
        },
        "EthernetStatus": {
            "table_summaries": ["Ethernet Statistics Table"],
            "keys": [
                "Line State",
                "Current Speed (Mbps)",
                "Current Duplex",
            ],
        },
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
    mappings = {}

    def normalize_key(k):
        k = k.replace(" ", "_").lower()
        k = re.sub(r"\([A-Za-z]+\)$", "", k)
        return k.strip("_")

    def set_value(description, value_element):
        key = normalize_key(description)
        value = value_element.text.strip()
        try:
            v = float(value)
        except ValueError:
            v = value
        value = v
        results[key] = value
        mappings[key] = {"description": description}
        if isinstance(v, float):
            mappings[key]["type"] = "float"

    def lookup(key):
        value_element = soup.find("td", {"headers": key})
        if not value_element:
            return
        header_element = value_element.parent.find("th")
        if not header_element:
            return

        description = f"{result_prefix}{header_element.text.strip()}"
        down_up = re.search(r"([DU]S)\d$", key)
        if down_up:
            d1 = description
            d2 = ""
            if "(" in description:
                paren_index = description.index("(")
                d1 = description[0:paren_index].strip()
                d2 = description[paren_index:]

            description = " ".join([d1, down_up.group(1), d2])
        set_value(description, value_element)

    timed_table = soup.find("table", {"summary": "Table of timed statistics"})
    if timed_table:
        timed_table = timed_table.find_all("td")
    else:
        timed_table = []
    multi_line = soup.find("td", {"headers": f"Line2 LineState"}) is not None

    lines = [["", "Line1 ", 1]]
    if multi_line:
        lines = [
            [" Line1 ", "Line 1 ", 1],
            [" Line2 ", "Line 2 ", 2],
        ]
    for prefix, result_prefix, line in lines:
        for d in line_data:
            lookup(f"{prefix}{d}".strip())
        for d in ["DS", "US"]:
            for k in bi_dir_data:
                lookup(f"{prefix}{k} {d}{line}".strip())
        for t in time_data:
            lookup_key = f"{t}{prefix}".strip()
            # line endings are weird for time_keys, do it inefficiently
            headers = [f for f in timed_table if f.text and lookup_key in f.text]
            if headers:
                header = headers[0]
                value_element = header.parent.findAll("td")[-1]  # total
                description = re.sub(r"\([A-Z]+\)", "", t).strip()
                description = f"Line {line} {description}"

                set_value(description, value_element)

    for name, value in global_data.items():
        keys = value["keys"]
        table_summaries = value["table_summaries"]
        tables = [soup.find("table", {"summary": table}) for table in table_summaries]
        tables = [x for x in tables if x]
        if not len(tables) > 0:
            continue
        table = tables[0]
        for key in keys:
            th = table.find("th", string=key)
            if not th:
                continue
            value_element = th.parent.find("td")
            description = key

            set_value(description, value_element)

    if mapping:
        return json.dumps(mappings, indent=2, sort_keys=True)
    else:
        return json.dumps(results, indent=2, sort_keys=True)


hostName = ""
serverPort = 8080


class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        response = parse()
        if self.path.endswith("/mappings"):
            response = parse(mapping=True)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(bytes(response, "utf-8"))


if __name__ == "__main__":
    mode = os.environ.get("MODE", None)
    if mode:
        if mode == "SERVER":
            webServer = HTTPServer((hostName, serverPort), MyServer)
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