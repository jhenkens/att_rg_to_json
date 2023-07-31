def build_home_assistant_data_response(converted_data):
    result = {x["id"]: x["value"] for x in converted_data}
    sorted_keys = sorted(result.keys())
    return {k: result[k] for k in sorted_keys}

def build_homeassistant_rest_sensor_template(converted_data, server_addr):
    sensors = "\n".join([sensor_data(n) for n in converted_data])
    return f"""
rest:
  - scan_interval: 30
    resource: "{server_addr}/ha"
    sensor:
{sensors}
""".strip()

def sensor_data(entry):
    lines = {
        "name": f"ATT RG {entry['name']}",
        "value_template": "{{ value_json." + entry['id'] +" }}",
        "unique_id": f"att_rg_rest_{ entry['id'] }",
    }
    if isinstance(entry["value"], float):
        lines["state_class"] = "measurement"
        lines["value_template"] = "{{ value_json." + entry['id'] + " | float }}"
    if entry.get("unit"):
        lines["unit_of_measurement"] = entry["unit"]
    lines = [f'{k}: "{v}"' for k,v in lines.items()]
    line0 = ["      - " + n for n in lines[0:1]]
    lines = ["        " + n for n in lines[1:]]
    lines = line0 + lines
    return "\n".join(lines)
