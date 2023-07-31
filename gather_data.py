#!/usr/bin/env python3
from bs4 import BeautifulSoup
import json, requests

MODEM_URL = "http://192.168.1.254/cgi-bin/broadbandstatistics.ha"
NON_BREAK_SPACE = "\xa0"


def sanitize(s):
    if s:
        if isinstance(s, str):
            s = s.strip()
    return s


def _s(s):
    return sanitize(s)


def strip_dict(d):
    return {k: v for k, v in d.items() if k and v}


def _d(d):
    return strip_dict(d)

def strip_arr(a):
    return [v for v in a if v]

def _a(a):
    return strip_arr(a)


def get_tables_from_soup():
    page = requests.get(MODEM_URL, timeout=10)
    soup = BeautifulSoup(page.content, "html.parser")
    tables = soup.find_all("table")
    return tables


def parse_table(results, table):
    result = {}
    table_name = table.attrs["summary"]
    if table_name in results:
        raise ValueError("Should not find multiple tables with the same name")
    results[table_name] = result

    categories = []
    rows = table.find_all("tr")
    for row in rows:
        th = row.find_all("th")
        cols = row.find_all("td")

        if len(th) > 1:
            categories = [_d({"id": _s(cat.attrs.get('id')), "text": _s(cat.text)}) for cat in th[1:]]
            continue
        
        if not th:
            if cols and cols[0] and cols[0].attrs.get("scope") == "row":
                th = cols[0]
                cols = cols[1:]
            else:
                continue
        else:
            th = th[0]

        current_result = {}
        current_result["title"] = _s(th.text)
        values = []
        for idx, col in enumerate(cols):
            value = {"value": _s(col.text), "id": _s(col.attrs.get('id'))}
            if len(cols) == len(categories):
                value["category"] = categories[idx]
            values.append(_d(value))
        current_result["values"] = _a(values)

        result[current_result["title"]] = current_result


def parse_all():
    tables = get_tables_from_soup()
    results = {}
    for table in tables:
        parse_table(results, table)
    return results