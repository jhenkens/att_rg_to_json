#!/usr/bin/env python3
from bs4 import BeautifulSoup
import sys, json, requests, re, os
from http.server import BaseHTTPRequestHandler, HTTPServer
import warnings

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
        "Errored Seconds (ES)",
        "Severely Errored Seconds (SESL)",
        "Unavailable Seconds (UASL)",
        "DSL Initialization Timeouts",
    ]
    results = {}
    mappings = {}

    def normalize_key(k):
        k = k.replace(" ", "_").lower()
        k = re.sub(r"\([A-Za-z]+\)[_]*", "", k)
        return k.strip("_")

    def set_value(description, value_element):
        description = re.sub(r"\s+", " ", description)
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

    def lookup(key, result_prefix, suffix=None):
        def join_headers(td):
            if not td.attrs:
                return None
            if not 'headers' in td.attrs:
                return None
            headers = td.attrs['headers']
            if isinstance(headers, list):
                headers = " ".join(headers)
            return headers
            
        def test_key(td):
            headers = join_headers(td)
            return headers and re.match(key, headers)
        value_element = [td for td in soup.find_all("td") if test_key(td)]
        value_element = value_element[0] if value_element else None
        if not value_element:
            return
        header_element = value_element.parent.find("th")
        if not header_element:
            return
        
        key_text = join_headers(value_element)

        description = f"{result_prefix} {header_element.text.strip()}"
        down_up = re.search(r"([DU]S)\d$", key_text)
        if down_up:
            d1 = description
            d2 = ""
            if "(" in description:
                paren_index = description.index("(")
                d1 = description[0:paren_index].strip()
                d2 = description[paren_index:]

            description = " ".join([d1, down_up.group(1), d2])
        if suffix:
            description = description.strip() + " " + suffix
        set_value(description, value_element)

    timed_table = soup.find("table", {"summary": "Table of timed statistics"})
    if timed_table:
        timed_table = timed_table.find_all("td")
    else:
        timed_table = []
    multi_line = soup.find("td", {"headers": f"Line2 LineState"}) is not None

    lines = [1]
    if multi_line:
        lines = [1,2]
        
    for line_number in lines:
        result_prefix = f"Line {line_number}"
        
        line_regex = f"Line{line_number}"
        if not multi_line:
            line_regex = ""

        for key in line_data:
            lookup(rf"^\s*{line_regex}\s*{key}\s*$", result_prefix)
        
        for direction in ["DS", "US"]:
            for key in bi_dir_data:
                suffix = None
                if "seconds" in key.lower():
                    suffix = "Current Day"
                lookup(rf"^\s*{line_regex}\s*{key}\s*{direction}\s*{line_number}\s*$", result_prefix, suffix=suffix)
        
        for key in time_data:
            key = key.replace(' ', r"\s")
            key = key.replace('(', r'\(')
            key = key.replace(')', r'\)')
            lookup_key = rf"^\s*{key}\s*Line\s*{line_number}\s*$"
            # line endings are weird for time_keys, do it inefficiently
            headers = [f for f in timed_table if f.text and re.match(lookup_key, f.text)]
            if headers:
                header = headers[0]
                value_element = header.parent.findAll("td")[-1]  # total
                description = re.sub(r"\([A-Z]+\)?\s*line\s*\d$", "", header.text, flags=re.IGNORECASE ).strip()
                description = f"Line {line_number} {description}"

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
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore",category=DeprecationWarning)
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