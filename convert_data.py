import re

category_mappings = {
    "line1": {"id": "line_1", "name": "Line 1", "specifies_line": True },
    "line2": {"id": "line_2", "name": "Line 2", "specifies_line": True },
    "us1": {"id": "line_1_us", "name": "Line 1 Upstream", "specifies_line": True },
    "ds1": {"id": "line_1_ds", "name": "Line 1 Downstream", "specifies_line": True },
    "us2": {"id": "line_2_us", "name": "Line 2 Upstream", "specifies_line": True },
    "ds2": {"id": "line_2_ds", "name": "Line 2 Downstream", "specifies_line": True },
}

ignore_segments = ["(SESL)", "(ES)", "(UASL)"]
ignore_segments = [v.lower() for v in ignore_segments]

units_segments = r"(\((?:kbps|dBm|db)\))"
line_matcher = r"Line\s*(\d)"

def should_prefix_with_table_name(table_name):
    return re.search(r"^ipv\d", table_name, flags=re.IGNORECASE) is not None

def parse_line_from_entry_name(entry_name):
    line = re.search(line_matcher, entry_name, flags=re.IGNORECASE)
    if line:
        line = line.group(1)
    else:
        line = None
    entry_name = re.sub(line_matcher, "", entry_name, flags=re.IGNORECASE).strip()
    return (entry_name, line)

def parse_cat(value):
    cat = value.get("category")
    cat_id = None
    cat_name = None
    if cat:
        cat_id = cat.get("id")
        if cat_id and cat_id.lower() in category_mappings:
            cat = category_mappings[cat_id.lower()]
            return cat
        else:
            cat_name = cat.get("text")
    
    result = {}
    if cat_id:
        result["id"] = cat_id
    elif cat_name:
        result["id"] = re.sub(r"\s+", "_", cat_name).lower()
    if cat_name:
        result["name"] = cat_name
    elif cat_id:
        result["name"] = cat_id

    return result
    
    
def build_name_and_id(entry_name, table_name, cat, line):
    if should_prefix_with_table_name(table_name):
        table_name = re.sub("\s*Table\s*$", "", table_name, flags=re.IGNORECASE).strip()
        entry_name = f"{table_name} {entry_name}".strip()
    entry_name = [x.strip() for x in entry_name.split(" ")]
    entry_name = [x for x in entry_name if x]
    entry_name = [x for x in entry_name if not x.lower() in ignore_segments]
    id = [x.lower() for x in entry_name]

    if cat:
        entry_name = [cat["name"]] + entry_name
        id = [cat["id"]] + id

    if (not cat or not cat.get("line_specified")) and line is not None:
        entry_name = ["line", line] + entry_name
        id = ["line", line] + id
        

    entry_name = " ".join(entry_name)
    id = "_".join(id)
    return (entry_name, id)

    
def parse_unit(entry_name):
    unit = re.search(units_segments, entry_name, flags=re.IGNORECASE)

    if unit:
        unit = unit.group(0)
        entry_name = entry_name.replace(unit, "")
        unit = unit.strip("()")
    else:
        unit = None
    return (entry_name, unit)
        

time_series_re = r"(?:15_min|cur_day|(?:(?:last_)?showtime))_"
total_renamer = r"total_"
def filter_results(results):
    for result in results:
        if re.search(time_series_re, result["id"]):
            continue
        if re.search(total_renamer, result["id"]):
            result["id"] = re.sub(total_renamer, "", result["id"])
        yield result    

def convert(raw):
    results = []
    for table_name, table in raw.items():
        for _, entry in table.items():
            entry_name = entry["title"]
            entry_name = re.sub(r"\s+", " ", entry_name).strip()
            entry_name, line = parse_line_from_entry_name(entry_name)

            values = entry["values"]
            if not values:
                values = [{"value":""}]

            for value in values:
                result = {}
                name = entry_name

                cat = parse_cat(value)
                name, unit = parse_unit(name)
                name, id = build_name_and_id(name, table_name, cat, line)

                result["name"] = name
                result["id"] = id
                if unit:
                    result["unit"] = unit.strip("()")
                value = value["value"]
                if isinstance(value, str) and re.search(r"^\d+(?:\.\d+)?$", value):
                    value = float(value)
                
                result["value"] = value
                results.append(result)
    return [x for x in filter_results(results)]
