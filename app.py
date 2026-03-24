from flask import Flask, jsonify, render_template, request
from Longetivity import collect_metrics, collect_metrics_by_type, get_latest_metrics, get_latest_metrics_on_load, get_core_dumps_output
import time
import pandas as pd
import json

app = Flask(__name__)

# Load device type mappings
with open("data.json", "r") as f:
    data = json.load(f)

# Create a mapping of device names to types
device_type_map = {device["name"]: device["type"] for device in data["devices"]}

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/initial-data", methods=["GET"])
def initial_data():
    """
    Get the latest data from Excel file without executing any commands.
    Used for initial page load.
    """
    try:
        data = get_latest_metrics_on_load()
        
        if data is None:
            return jsonify({"status": "no_data", "message": "No data available, press refresh button to get data"})
        
        # Add device type to the response for filtering
        return jsonify({"status": "success", "data": data, "filter_type": "all"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/refresh", methods=["GET"])
def refresh():
    """
    Refresh metrics with optional device type filter.
    Query parameter: type (vsrx, highend, branch, spc3, or all)
    """
    try:
        device_type = request.args.get('type', 'all')
        
        if device_type == 'all':
            collect_metrics()
        elif device_type in ['vsrx', 'highend', 'branch', 'spc3']:
            collect_metrics_by_type(device_type)
        else:
            return jsonify({"status": "error", "message": f"Invalid device type: {device_type}"})

        time.sleep(5)  # Wait for metrics to be collected

        data = get_latest_metrics()
        
        # Filter data based on device type if not 'all'
        if device_type != 'all' and data.get('security'):
            filtered_security = []
            for row in data['security']:
                hostname = row.get('Hostname', '')
                # Extract device name from hostname (remove domain)
                device_name = hostname.split('.')[0]
                
                # Check if this device matches the requested type
                if device_name in device_type_map and device_type_map[device_name] == device_type:
                    filtered_security.append(row)
            
            data['security'] = filtered_security
        
        return jsonify({"status": "success", "data": data, "filter_type": device_type})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/latest-data", methods=["GET"])
def latest_data():
    """
    Fetch only the latest data from Excel without executing commands.
    """
    try:
        data = get_latest_metrics_on_load()
        
        if data is None:
            return jsonify({"status": "no_data", "message": "No data available in Excel file"})
        
        return jsonify({"status": "success", "data": data, "filter_type": "all"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/core-dumps/<hostname>", methods=["GET"])
def get_core_dumps(hostname):
    """
    Get the core dumps output for a specific hostname
    """
    try:
        output = get_core_dumps_output(hostname)
        return jsonify({"status": "success", "hostname": hostname, "output": output})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
