import time
import json
import paramiko
from netmiko import ConnectHandler
from paramiko import AutoAddPolicy
import re
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import os

# Thread-safe lock for Excel file writing
excel_lock = threading.Lock()

# Excel file name constant
EXCEL_FILE = "security_monitoring.xlsx"

# ========== Load Data ==========
with open("data.json", "r") as f:
    data = json.load(f)

# ========== Connection Functions ==========
def get_handle_junos_netmiko(host, device_type="juniper_junos"):
    device = {
        'device_type': device_type,
        'host': host,
        'username': data["ssh-username"],
        'password': data["ssh-password"],
        'port': 22,
        'timeout': 30,
        'fast_cli': False,
    }
    while True:
        try:
            print(f"[INFO] Connecting to JUNOS device: {host}")
            return ConnectHandler(**device)
        except Exception as e:
            print(f"[RETRY] Netmiko connection to {host} failed: {e}")
            time.sleep(5)

def get_handle(host, username="root", pwd="Embe1mpls", max_tries=3):
    if host == data.get('esst-srv2-arm'):
        username = "root"
        pwd = data["esst-srv2-arm-password"]
    elif host in [data.get('ttbg'), data.get('ttsv')]:
        username = data["cred"]
        pwd = data["pwd"]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    for _ in range(max_tries):
        try:
            ssh.connect(host, username=username, password=pwd, timeout=40)
            print(f"[INFO] SSH connection established with {host}")
            return {"ssh": ssh}
        except Exception as e:
            print(f"[RETRY] SSH to {host} failed: {e}")
            time.sleep(5)
    raise Exception(f"[ERROR] Failed to connect to {host}")

# ========== Parse Functions ==========
def parse_show_version(output):
    """
    Parse 'show version' output and extract Hostname, Model, and Junos version.
    """
    print("[INFO] Parsing 'show version' output...")
    
    hostname = None
    model = None
    junos = None
    
    lines = output.strip().split('\n')
    for line in lines:
        if "Hostname:" in line:
            hostname = line.split("Hostname:")[1].strip()
        elif "Model:" in line:
            model = line.split("Model:")[1].strip()
        elif "Junos:" in line:
            junos = line.split("Junos:")[1].strip()
    
    print(f"[PARSED] Hostname={hostname}, Model={model}, Junos={junos}")
    return hostname, model, junos

def parse_chassis_hardware(output):
    """
    Parse 'show chassis hardware' output and extract Routing Engine Description.
    """
    print("[INFO] Parsing 'show chassis hardware' output...")
    
    routing_engine_desc = None
    
    lines = output.strip().split('\n')
    for line in lines:
        # Look for "Routing Engine" line and extract description
        if "Routing Engine" in line:
            # Split by multiple spaces to get columns
            parts = re.split(r'\s{2,}', line.strip())
            # Description is typically the last column
            if len(parts) > 0:
                routing_engine_desc = parts[-1]
                break
    
    print(f"[PARSED] Routing Engine Description={routing_engine_desc}")
    return routing_engine_desc

def parse_security_monitoring(output):
    """
    Parse the 'show security monitoring' output and extract CPU, Mem, Flow session current, and CP session current.
    """
    print("[INFO] Parsing 'show security monitoring' output...")
    
    if not output or len(output.strip()) < 20:
        print("[WARNING] Security monitoring output is empty or too short")
        return []
    
    lines = output.strip().split('\n')
    
    parsed_data = []
    for line in lines:
        # Split by whitespace
        parts = line.strip().split()
        
        # Skip empty lines
        if not parts:
            continue
        
        # Skip header lines
        if "FPC" in line or "Flow" in line or "session" in line or "current" in line or "maximum" in line:
            continue
        
        # Skip command prompts and echoes
        if ">" in line or "#" in line or "show security monitoring" in line:
            continue
        
        # Check if this is a data line (should start with numbers for FPC PIC CPU Mem)
        # Must have at least 8 parts: FPC PIC CPU Mem Flow-current Flow-max CP-current CP-max
        if len(parts) >= 8:
            try:
                # Verify first 4 elements can be digits (FPC, PIC, CPU, Mem)
                if not (parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit() and parts[3].isdigit()):
                    continue
                
                # Extract the values
                cpu = parts[2]
                mem = parts[3]
                flow_session_current = parts[4]
                # CP session current is at index 6 (skip flow maximum at index 5)
                cp_session_current = parts[6] if len(parts) > 6 else "N/A"
                
                parsed_data.append({
                    'CPU': cpu,
                    'Memory': mem,
                    'Flow Session Current': flow_session_current,
                    'CP Session Current': cp_session_current
                })
                
                print(f"[PARSED] CPU={cpu}, Mem={mem}, Flow Session Current={flow_session_current}, CP Session Current={cp_session_current}")
                
            except Exception as e:
                print(f"[WARNING] Failed to parse line: {line.strip()} - Error: {e}")
                continue
    
    if not parsed_data:
        print("[WARNING] No security monitoring data was parsed from output")
        # Print first few lines for debugging
        print(f"[DEBUG] First 5 lines of output:")
        for i, line in enumerate(lines[:5]):
            print(f"[DEBUG] Line {i}: {repr(line)}")
    
    return parsed_data

def parse_security_monitoring_spc3(output):
    """
    Parse the 'show security monitoring' output for SPC3 devices.
    For SPC3, we need CPU and Mem for FPC 1 PIC 1, and Total Sessions data.
    """
    print("[INFO] Parsing 'show security monitoring' output for SPC3...")
    
    if not output or len(output.strip()) < 20:
        print("[WARNING] Security monitoring output is empty or too short")
        return []
    
    lines = output.strip().split('\n')
    
    cpu = None
    mem = None
    flow_session_current = None
    cp_session_current = None
    
    for line in lines:
        parts = line.strip().split()
        
        if not parts:
            continue
        
        # Look for FPC 1 PIC 1 line
        if len(parts) >= 4 and parts[0] == "1" and parts[1] == "1":
            try:
                if parts[2].isdigit() and parts[3].isdigit():
                    cpu = parts[2]
                    mem = parts[3]
                    print(f"[PARSED] Found FPC 1 PIC 1: CPU={cpu}, Mem={mem}")
            except Exception as e:
                print(f"[WARNING] Failed to parse FPC 1 PIC 1 line: {e}")
        
        # Look for Total Sessions line
        if "Total Sessions:" in line or "total sessions:" in line.lower():
            try:
                # Format: "Total Sessions:              0       39321600              0       47185920"
                # After "Total Sessions:" we have: current, max, current, max
                total_idx = None
                for i, part in enumerate(parts):
                    if "sessions:" in part.lower():
                        total_idx = i
                        break
                
                if total_idx is not None and len(parts) > total_idx + 3:
                    flow_session_current = parts[total_idx + 1]
                    cp_session_current = parts[total_idx + 3]
                    print(f"[PARSED] Total Sessions: Flow={flow_session_current}, CP={cp_session_current}")
            except Exception as e:
                print(f"[WARNING] Failed to parse Total Sessions line: {e}")
    
    if cpu and mem and flow_session_current is not None and cp_session_current is not None:
        parsed_data = [{
            'CPU': cpu,
            'Memory': mem,
            'Flow Session Current': flow_session_current,
            'CP Session Current': cp_session_current
        }]
        print(f"[PARSED] SPC3 Final: CPU={cpu}, Mem={mem}, Flow Session Current={flow_session_current}, CP Session Current={cp_session_current}")
        return parsed_data
    else:
        print(f"[WARNING] Incomplete SPC3 security monitoring data: CPU={cpu}, Mem={mem}, Flow={flow_session_current}, CP={cp_session_current}")
        return []

def parse_arena(output):
    """
    Parse 'request pfe execute command "sh arena" target fwdd' output and extract Global Data SHM percentage.
    """
    print("[INFO] Parsing 'sh arena' output...")
    
    global_data_shm_percent = None
    
    lines = output.strip().split('\n')
    for line in lines:
        # Look for "global data SHM" line (case insensitive)
        if "global data shm" in line.lower():
            # Parse the line to extract percentage
            # Format: " 2    65d8f580    6341787648    4066359904    2275427744   35  global data SHM"
            # The columns are: ID Base Total(b) Free(b) Used(b) % Name
            parts = re.split(r'\s+', line.strip())
            
            # Find the index of "global" keyword
            global_idx = None
            for i, part in enumerate(parts):
                if part.lower() == "global":
                    global_idx = i
                    break
            
            # The percentage should be right before "global"
            if global_idx and global_idx > 0:
                try:
                    potential_percent = parts[global_idx - 1]
                    if potential_percent.isdigit():
                        global_data_shm_percent = potential_percent
                        break
                except:
                    pass
    
    # Return "0" if not found instead of None to avoid JSON errors
    result = global_data_shm_percent if global_data_shm_percent else "0"
    print(f"[PARSED] Global Data SHM(%)={result}")
    return result

def parse_system_core_dumps(output):
    """
    Parse 'show system core-dumps' output and return 'Yes' if core files exist, 'No' otherwise.
    Also return the full output for later display.
    """
    print("[INFO] Parsing 'show system core-dumps' output...")
    
    lines = output.strip().split('\n')
    cores_found = False
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
        
        # Skip lines with "No such file or directory"
        if "No such file or directory" in line:
            continue
            
        # Skip directory headers (lines ending with :)
        if line.strip().endswith(':'):
            continue
            
        # Skip lines with total blocks/files headers
        if "total blocks:" in line.lower() or "total files:" in line.lower():
            continue
        
        # Skip command echo and prompts
        if "show system core-dumps" in line or ">" in line or "#" in line:
            continue
        
        # Check if the line contains the keyword "core" (case insensitive)
        # This indicates an actual core file is present
        if "core" in line.lower():
            cores_found = True
            print(f"[PARSED] Found core file in line: {line.strip()}")
            break
    
    result = "Yes" if cores_found else "No"
    print(f"[PARSED] Core dumps found: {result}")
    return result, output

# ========== Device-Type Specific Command Functions ==========

def run_commands_vsrx(ttbg_shell, device_name):
    """
    Run vSRX specific commands
    """
    print(f"[INFO] Running vSRX commands for {device_name}")
    outputs = {}
    
    # Show version
    print(f"[{device_name}] Executing: show version | no-more")
    ttbg_shell.send("show version | no-more\n")
    time.sleep(5)
    outputs['version'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['version'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['version'] and len(outputs['version'].strip()) > 50:
        if "error" in outputs['version'].lower() or "invalid" in outputs['version'].lower():
            print(f"[{device_name}] ✗ show version: Error in output")
        else:
            print(f"[{device_name}] ✓ show version: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show version: No output received or insufficient data")
    
    # Show chassis hardware
    print(f"[{device_name}] Executing: show chassis hardware")
    ttbg_shell.send("show chassis hardware | no-more\n")
    time.sleep(5)
    outputs['chassis'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['chassis'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['chassis'] and len(outputs['chassis'].strip()) > 30:
        if "error" in outputs['chassis'].lower() or "invalid" in outputs['chassis'].lower():
            print(f"[{device_name}] ✗ show chassis hardware: Error in output")
        else:
            print(f"[{device_name}] ✓ show chassis hardware: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show chassis hardware: No output received or insufficient data")
    
    # Show security monitoring
    print(f"[{device_name}] Executing: show security monitoring")
    ttbg_shell.send("show security monitoring\n")
    time.sleep(8)
    outputs['monitoring'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['monitoring'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['monitoring'] and len(outputs['monitoring'].strip()) > 30:
        if "error" in outputs['monitoring'].lower() or "invalid" in outputs['monitoring'].lower():
            print(f"[{device_name}] ✗ show security monitoring: Error in output")
        else:
            print(f"[{device_name}] ✓ show security monitoring: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show security monitoring: No output received or insufficient data")
    
    # Show system core-dumps
    print(f"[{device_name}] Executing: show system core-dumps")
    ttbg_shell.send("  \n")
    time.sleep(8)
    outputs['core_dumps'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['core_dumps'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['core_dumps'] and len(outputs['core_dumps'].strip()) > 20:
        if "error" in outputs['core_dumps'].lower() and "no such file" not in outputs['core_dumps'].lower():
            print(f"[{device_name}] ✗ show system core-dumps: Error in output")
        else:
            print(f"[{device_name}] ✓ show system core-dumps: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show system core-dumps: No output received or insufficient data")
    
    # Request pfe execute command "sh arena" target fwdd
    print(f"[{device_name}] Executing: request pfe execute command \"sh arena\" target fwdd")
    ttbg_shell.send('request pfe execute command "sh arena" target fwdd\n')
    time.sleep(15)
    outputs['arena'] = ""
    for _ in range(8):
        if ttbg_shell.recv_ready():
            outputs['arena'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['arena'] and len(outputs['arena'].strip()) > 50:
        if "error" in outputs['arena'].lower() or "invalid" in outputs['arena'].lower():
            print(f"[{device_name}] ✗ sh arena: Error in output")
        else:
            print(f"[{device_name}] ✓ sh arena: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ⚠ sh arena: Waiting for delayed output...")
        # Additional wait for slow responses
        time.sleep(10)
        for _ in range(5):
            if ttbg_shell.recv_ready():
                outputs['arena'] += ttbg_shell.recv(4096).decode(errors='ignore')
            time.sleep(2)
        
        if outputs['arena'] and len(outputs['arena'].strip()) > 50:
            print(f"[{device_name}] ✓ sh arena: Output received after delay and ready for parsing")
        else:
            print(f"[{device_name}] ✗ sh arena: No output received even after extended wait")
    
    return outputs

def run_commands_highend(ttbg_shell, device_name):
    """
    Run High-End device specific commands
    """
    print(f"[INFO] Running High-End commands for {device_name}")
    outputs = {}
    
    # Show version
    print(f"[{device_name}] Executing: show version | no-more")
    ttbg_shell.send("show version | no-more\n")
    time.sleep(5)
    outputs['version'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['version'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['version'] and len(outputs['version'].strip()) > 50:
        if "error" in outputs['version'].lower() or "invalid" in outputs['version'].lower():
            print(f"[{device_name}] ✗ show version: Error in output")
        else:
            print(f"[{device_name}] ✓ show version: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show version: No output received or insufficient data")
    
    # Show chassis hardware
    print(f"[{device_name}] Executing: show chassis hardware")
    ttbg_shell.send("show chassis hardware | no-more\n")
    time.sleep(5)
    outputs['chassis'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['chassis'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['chassis'] and len(outputs['chassis'].strip()) > 30:
        if "error" in outputs['chassis'].lower() or "invalid" in outputs['chassis'].lower():
            print(f"[{device_name}] ✗ show chassis hardware: Error in output")
        else:
            print(f"[{device_name}] ✓ show chassis hardware: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show chassis hardware: No output received or insufficient data")
    
    # Show security monitoring
    print(f"[{device_name}] Executing: show security monitoring")
    ttbg_shell.send("show security monitoring\n")
    time.sleep(8)
    outputs['monitoring'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['monitoring'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['monitoring'] and len(outputs['monitoring'].strip()) > 30:
        if "error" in outputs['monitoring'].lower() or "invalid" in outputs['monitoring'].lower():
            print(f"[{device_name}] ✗ show security monitoring: Error in output")
        else:
            print(f"[{device_name}] ✓ show security monitoring: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show security monitoring: No output received or insufficient data")
    
    # Show system core-dumps
    print(f"[{device_name}] Executing: show system core-dumps")
    ttbg_shell.send("show system core-dumps | no-more\n")
    time.sleep(8)
    outputs['core_dumps'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['core_dumps'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['core_dumps'] and len(outputs['core_dumps'].strip()) > 20:
        if "error" in outputs['core_dumps'].lower() and "no such file" not in outputs['core_dumps'].lower():
            print(f"[{device_name}] ✗ show system core-dumps: Error in output")
        else:
            print(f"[{device_name}] ✓ show system core-dumps: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show system core-dumps: No output received or insufficient data")
    
    # Request pfe execute command "sh arena" target fpc0 (High-End specific)
    print(f"[{device_name}] Executing: request pfe execute command \"sh arena\" target fpc0")
    ttbg_shell.send('request pfe execute command "sh arena" target fpc0\n')
    time.sleep(20)
    outputs['arena'] = ""
    for _ in range(8):
        if ttbg_shell.recv_ready():
            outputs['arena'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['arena'] and len(outputs['arena'].strip()) > 50:
        if "error" in outputs['arena'].lower() or "invalid" in outputs['arena'].lower():
            print(f"[{device_name}] ✗ sh arena: Error in output")
        else:
            print(f"[{device_name}] ✓ sh arena: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ⚠ sh arena: Waiting for delayed output...")
        # Additional wait for slow responses
        time.sleep(10)
        for _ in range(5):
            if ttbg_shell.recv_ready():
                outputs['arena'] += ttbg_shell.recv(4096).decode(errors='ignore')
            time.sleep(2)
        
        if outputs['arena'] and len(outputs['arena'].strip()) > 50:
            print(f"[{device_name}] ✓ sh arena: Output received after delay and ready for parsing")
        else:
            print(f"[{device_name}] ✗ sh arena: No output received even after extended wait")
    
    return outputs

def run_commands_branch(ttbg_shell, device_name):
    """
    Run Branch device specific commands
    """
    print(f"[INFO] Running Branch device commands for {device_name}")
    outputs = {}
    
    # Show version
    print(f"[{device_name}] Executing: show version | no-more")
    ttbg_shell.send("show version | no-more\n")
    time.sleep(5)
    outputs['version'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['version'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['version'] and len(outputs['version'].strip()) > 50:
        if "error" in outputs['version'].lower() or "invalid" in outputs['version'].lower():
            print(f"[{device_name}] ✗ show version: Error in output")
        else:
            print(f"[{device_name}] ✓ show version: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show version: No output received or insufficient data")
    
    # Show chassis hardware
    print(f"[{device_name}] Executing: show chassis hardware")
    ttbg_shell.send("show chassis hardware | no-more\n")
    time.sleep(5)
    outputs['chassis'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['chassis'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['chassis'] and len(outputs['chassis'].strip()) > 30:
        if "error" in outputs['chassis'].lower() or "invalid" in outputs['chassis'].lower():
            print(f"[{device_name}] ✗ show chassis hardware: Error in output")
        else:
            print(f"[{device_name}] ✓ show chassis hardware: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show chassis hardware: No output received or insufficient data")
    
    # Show security monitoring
    print(f"[{device_name}] Executing: show security monitoring")
    ttbg_shell.send("show security monitoring\n")
    time.sleep(8)
    outputs['monitoring'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['monitoring'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['monitoring'] and len(outputs['monitoring'].strip()) > 30:
        if "error" in outputs['monitoring'].lower() or "invalid" in outputs['monitoring'].lower():
            print(f"[{device_name}] ✗ show security monitoring: Error in output")
        else:
            print(f"[{device_name}] ✓ show security monitoring: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show security monitoring: No output received or insufficient data")
    
    # Show system core-dumps
    print(f"[{device_name}] Executing: show system core-dumps")
    ttbg_shell.send("show system core-dumps | no-more\n")
    time.sleep(8)
    outputs['core_dumps'] = ""
    for _ in range(5):
        if ttbg_shell.recv_ready():
            outputs['core_dumps'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['core_dumps'] and len(outputs['core_dumps'].strip()) > 20:
        if "error" in outputs['core_dumps'].lower() and "no such file" not in outputs['core_dumps'].lower():
            print(f"[{device_name}] ✗ show system core-dumps: Error in output")
        else:
            print(f"[{device_name}] ✓ show system core-dumps: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show system core-dumps: No output received or insufficient data")
    
    # Request pfe execute command "sh arena" target fwdd (Branch specific)
    print(f"[{device_name}] Executing: request pfe execute command \"sh arena\" target fwdd")
    ttbg_shell.send('request pfe execute command "sh arena" target fwdd\n')
    time.sleep(15)
    outputs['arena'] = ""
    for _ in range(8):
        if ttbg_shell.recv_ready():
            outputs['arena'] += ttbg_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['arena'] and len(outputs['arena'].strip()) > 50:
        if "error" in outputs['arena'].lower() or "invalid" in outputs['arena'].lower():
            print(f"[{device_name}] ✗ sh arena: Error in output")
        else:
            print(f"[{device_name}] ✓ sh arena: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ⚠ sh arena: Waiting for delayed output...")
        # Additional wait for slow responses
        time.sleep(10)
        for _ in range(5):
            if ttbg_shell.recv_ready():
                outputs['arena'] += ttbg_shell.recv(4096).decode(errors='ignore')
            time.sleep(2)
        
        if outputs['arena'] and len(outputs['arena'].strip()) > 50:
            print(f"[{device_name}] ✓ sh arena: Output received after delay and ready for parsing")
        else:
            print(f"[{device_name}] ✗ sh arena: No output received even after extended wait")
    
    return outputs

def run_commands_spc3(arm_shell, device_name):
    """
    Run SPC3 specific commands (srx5800x with SPC3 card)
    """
    print(f"[INFO] Running SPC3 commands for {device_name}")
    outputs = {}
    
    # Show version
    print(f"[{device_name}] Executing: show version | no-more")
    arm_shell.send("show version | no-more\n")
    time.sleep(5)
    outputs['version'] = ""
    for _ in range(5):
        if arm_shell.recv_ready():
            outputs['version'] += arm_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['version'] and len(outputs['version'].strip()) > 50:
        if "error" in outputs['version'].lower() or "invalid" in outputs['version'].lower():
            print(f"[{device_name}] ✗ show version: Error in output")
        else:
            print(f"[{device_name}] ✓ show version: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show version: No output received or insufficient data")
    
    # Show chassis hardware
    print(f"[{device_name}] Executing: show chassis hardware | no-more")
    arm_shell.send("show chassis hardware | no-more\n")
    time.sleep(5)
    outputs['chassis'] = ""
    for _ in range(5):
        if arm_shell.recv_ready():
            outputs['chassis'] += arm_shell.recv(4096).decode(errors='ignore')
        time.sleep(1)
    
    if outputs['chassis'] and len(outputs['chassis'].strip()) > 30:
        if "error" in outputs['chassis'].lower() or "invalid" in outputs['chassis'].lower():
            print(f"[{device_name}] ✗ show chassis hardware: Error in output")
        else:
            print(f"[{device_name}] ✓ show chassis hardware: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show chassis hardware: No output received or insufficient data")
    
    # Show security monitoring
    print(f"[{device_name}] Executing: show security monitoring")
    arm_shell.send("show security monitoring\n")
    time.sleep(8)
    outputs['monitoring'] = ""
    for _ in range(5):
        if arm_shell.recv_ready():
            outputs['monitoring'] += arm_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['monitoring'] and len(outputs['monitoring'].strip()) > 30:
        if "error" in outputs['monitoring'].lower() or "invalid" in outputs['monitoring'].lower():
            print(f"[{device_name}] ✗ show security monitoring: Error in output")
        else:
            print(f"[{device_name}] ✓ show security monitoring: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show security monitoring: No output received or insufficient data")
    
    # Show system core-dumps
    print(f"[{device_name}] Executing: show system core-dumps | no-more")
    arm_shell.send("show system core-dumps | no-more\n")
    time.sleep(8)
    outputs['core_dumps'] = ""
    for _ in range(5):
        if arm_shell.recv_ready():
            outputs['core_dumps'] += arm_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['core_dumps'] and len(outputs['core_dumps'].strip()) > 20:
        if "error" in outputs['core_dumps'].lower() and "no such file" not in outputs['core_dumps'].lower():
            print(f"[{device_name}] ✗ show system core-dumps: Error in output")
        else:
            print(f"[{device_name}] ✓ show system core-dumps: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ✗ show system core-dumps: No output received or insufficient data")
    
    # Request pfe execute command "sh arena" target tnp tnp-name fpc1.pic1
    print(f"[{device_name}] Executing: request pfe execute command \"sh arena\" target tnp tnp-name fpc1.pic1")
    arm_shell.send('request pfe execute command "sh arena" target tnp tnp-name fpc1.pic1\n')
    time.sleep(20)
    outputs['arena'] = ""
    for _ in range(8):
        if arm_shell.recv_ready():
            outputs['arena'] += arm_shell.recv(4096).decode(errors='ignore')
        time.sleep(2)
    
    if outputs['arena'] and len(outputs['arena'].strip()) > 50:
        if "error" in outputs['arena'].lower() or "invalid" in outputs['arena'].lower():
            print(f"[{device_name}] ✗ sh arena: Error in output")
        else:
            print(f"[{device_name}] ✓ sh arena: Output received and ready for parsing")
    else:
        print(f"[{device_name}] ⚠ sh arena: Waiting for delayed output...")
        # Additional wait for slow responses
        time.sleep(10)
        for _ in range(5):
            if arm_shell.recv_ready():
                outputs['arena'] += arm_shell.recv(4096).decode(errors='ignore')
            time.sleep(2)
        
        if outputs['arena'] and len(outputs['arena'].strip()) > 50:
            print(f"[{device_name}] ✓ sh arena: Output received after delay and ready for parsing")
        else:
            print(f"[{device_name}] ✗ sh arena: No output received even after extended wait")
    
    return outputs

# ========== Main Logic ==========
def login_and_run_commands(device_name, device_vm, device_type):
    """
    Login to esst-srv2-arm shell, then login to device, go to CLI mode,
    and run multiple show commands with enhanced error handling and retry logic.
    """
    print(f"==== Starting esst-srv2-arm to {device_name} Connection Process ====")
    
    max_login_retries = 3
    max_command_retries = 2
    
    for login_attempt in range(max_login_retries):
        try:
            # Step 1: Connect to esst-srv2-arm shell
            print(f"[INFO] Connecting to esst-srv2-arm shell... (Attempt {login_attempt + 1}/{max_login_retries})")
            arm_ssh = get_handle(data["esst-srv2-arm"])["ssh"]
            arm_shell = arm_ssh.invoke_shell()
            time.sleep(3)
            arm_shell.recv(65536)  # Clear initial output with larger buffer
            
            # Step 2: SSH from esst-srv2-arm to device
            print(f"[INFO] SSHing from esst-srv2-arm to device: {device_vm}")
            ssh_command = f"ssh {data['ssh-username']}@{device_vm}\n"
            arm_shell.send(ssh_command)
            
            # Handle SSH prompts with extended timeout
            output = ""
            login_success = False
            max_wait_iterations = 30  # 60 seconds total wait time
            
            for iteration in range(max_wait_iterations):
                time.sleep(2)
                if arm_shell.recv_ready():
                    chunk = arm_shell.recv(65536).decode(errors='ignore')
                    output += chunk
                    
                    # Check for connection errors FIRST before other conditions
                    if "no route to host" in chunk.lower():
                        raise Exception(f"No route to host - {device_name} is unreachable")
                    elif "connection refused" in chunk.lower():
                        raise Exception(f"Connection refused - {device_name} may be down")
                    elif "connection timed out" in chunk.lower():
                        raise Exception(f"Connection timed out - {device_name} is not responding")
                    elif "connection closed" in chunk.lower() and "password:" not in output.lower():
                        raise Exception(f"Connection closed unexpectedly for {device_name}")
                    elif "host key verification failed" in chunk.lower():
                        raise Exception(f"Host key verification failed for {device_name}")
                    
                    if "continue connecting" in chunk.lower() or "yes/no" in chunk.lower():
                        print("[INFO] Accepting SSH key...")
                        arm_shell.send("yes\n")
                        time.sleep(2)
                    elif "password:" in chunk.lower():
                        print("[INFO] Entering password...")
                        arm_shell.send(data["ssh-password"] + "\n")
                        time.sleep(3)
                    elif "permission denied" in chunk.lower() or "authentication failed" in chunk.lower():
                        raise Exception(f"Authentication failed for {device_name}")
                    elif "#" in chunk or "~" in chunk:
                        # Verify we're actually on the target device, not esst-srv2-arm
                        # Check if the prompt contains the device name or "root@<device>"
                        if device_name.split('.')[0] in output or f"root@{device_name.split('.')[0]}" in output:
                            print(f"[SUCCESS] Logged into {device_name}")
                            login_success = True
                            break
                        elif "esst-srv2-arm" in output:
                            # Still on jump host, continue waiting
                            continue
            
            if not login_success:
                raise Exception(f"Login timeout for {device_name} - no prompt received after {max_wait_iterations * 2} seconds")
            
            time.sleep(3)
            
            # Step 3: Enter CLI mode and verify we're in Junos CLI
            print("[INFO] Entering CLI mode...")
            arm_shell.send("cli\n")
            time.sleep(3)
            
            # Wait for CLI prompt and verify it's Junos
            cli_output = ""
            cli_ready = False
            for _ in range(10):
                if arm_shell.recv_ready():
                    cli_output += arm_shell.recv(65536).decode(errors='ignore')
                    
                    # Check if we got an error indicating we're not on a Junos device
                    if "command not found" in cli_output.lower() or "can be installed with" in cli_output.lower():
                        raise Exception(f"Not on a Junos device - CLI command not found. Still on jump host or wrong device.")
                    
                    # Look for Junos CLI prompt (user@hostname> or root@hostname>)
                    if ">" in cli_output and device_name.split('.')[0] in cli_output:
                        cli_ready = True
                        break
                time.sleep(1)
            
            if not cli_ready:
                raise Exception(f"Failed to enter CLI mode for {device_name}. May not be on correct device or device is not Junos.")
            
            print(f"[SUCCESS] CLI mode entered for {device_name}")
            
            # Step 4: Run device-type specific commands with retry logic
            outputs = None
            for cmd_attempt in range(max_command_retries):
                try:
                    print(f"[INFO] Running commands... (Attempt {cmd_attempt + 1}/{max_command_retries})")
                    
                    if device_type == "vsrx":
                        outputs = run_commands_vsrx(arm_shell, device_name)
                    elif device_type == "highend":
                        outputs = run_commands_highend(arm_shell, device_name)
                    elif device_type == "branch":
                        outputs = run_commands_branch(arm_shell, device_name)
                    elif device_type == "spc3":
                        outputs = run_commands_spc3(arm_shell, device_name)
                    else:
                        raise ValueError(f"[ERROR] Unknown device type: {device_type}. Valid types are: vsrx, highend, branch, spc3")
                    
                    # Verify outputs are not empty and contain Junos-specific content
                    if outputs and outputs.get('version') and len(outputs['version'].strip()) > 50:
                        # Check if version output contains Junos indicators
                        if "Hostname:" in outputs['version'] or "JUNOS" in outputs['version'] or "Model:" in outputs['version']:
                            print(f"[SUCCESS] Commands completed successfully for {device_name}")
                            break
                        else:
                            raise Exception("Output doesn't contain Junos device information - may be on wrong device")
                    else:
                        raise Exception("Commands returned empty or insufficient output")
                        
                except Exception as cmd_error:
                    print(f"[WARNING] Command execution attempt {cmd_attempt + 1} failed: {cmd_error}")
                    if cmd_attempt < max_command_retries - 1:
                        print("[INFO] Retrying commands...")
                        time.sleep(5)
                    else:
                        raise Exception(f"Commands failed after {max_command_retries} attempts: {cmd_error}")
            
            # Cleanup
            try:
                arm_shell.send("exit\n")
                time.sleep(2)
                arm_shell.send("exit\n")
                time.sleep(1)
                arm_ssh.close()
            except:
                pass
            
            print(f"[INFO] Connection closed for {device_name}")
            
            return outputs['version'], outputs['chassis'], outputs['monitoring'], outputs['core_dumps'], outputs['arena']
        
        except Exception as e:
            print(f"[ERROR] Login attempt {login_attempt + 1} failed for {device_name}: {e}")
            
            # Cleanup on failure
            try:
                if 'arm_ssh' in locals():
                    arm_ssh.close()
            except:
                pass
            
            if login_attempt < max_login_retries - 1:
                print(f"[INFO] Retrying login for {device_name}...")
                time.sleep(5)
            else:
                raise Exception(f"Failed to connect to {device_name} after {max_login_retries} attempts: {e}")

# ========== Save to Excel ==========
# Global dictionary to store core dumps output for devices with cores
core_dumps_storage = {}

def save_to_excel(hostname, model, junos, routing_engine_desc, security_data, cores, global_data_shm, core_dumps_output, filename="security_monitoring.xlsx", error_msg=None):
    """
    Save all parsed data to Excel file. Append if file exists.
    If error_msg is provided, save error information instead.
    """
    # Store core dumps output if cores are found
    if cores == "Yes":
        core_dumps_storage[hostname] = core_dumps_output
    
    # Combine all data into records
    records = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # If there's an error, save error record
    if error_msg:
        record = {
            'Timestamp': timestamp,
            'Hostname': hostname if hostname else "Unknown",
            'Model': model if model else "File Fetch Failed",
            'Junos': junos if junos else "File Fetch Failed",
            'Routing Engine': routing_engine_desc if routing_engine_desc else "File Fetch Failed",
            'CPU': "File Fetch Failed",
            'Memory': "File Fetch Failed",
            'Flow Session Current': "File Fetch Failed",
            'CP Session Current': "File Fetch Failed",
            'Cores': "File Fetch Failed",
            'Global Data SHM(%)': "File Fetch Failed"
        }
        records.append(record)
    # If security data exists, create one row per FPC/PIC
    elif security_data:
        for sec_data in security_data:
            record = {
                'Timestamp': timestamp,
                'Hostname': hostname,
                'Model': model,
                'Junos': junos,
                'Routing Engine': routing_engine_desc,
                'CPU': sec_data['CPU'],
                'Memory': sec_data['Memory'],
                'Flow Session Current': sec_data['Flow Session Current'],
                'CP Session Current': sec_data['CP Session Current'],
                'Cores': cores,
                'Global Data SHM(%)': global_data_shm
            }
            records.append(record)
    else:
        # If no security data, still save version and chassis info
        record = {
            'Timestamp': timestamp,
            'Hostname': hostname,
            'Model': model,
            'Junos': junos,
            'Routing Engine': routing_engine_desc,
            'CPU': None,
            'Memory': None,
            'Flow Session Current': None,
            'CP Session Current': None,
            'Cores': cores,
            'Global Data SHM(%)': global_data_shm
        }
        records.append(record)
    
    with excel_lock:
        try:
            # Try to read existing file
            existing_df = pd.read_excel(filename)
            print(f"[INFO] Appending to existing file: {filename}")
            # Append new data
            df = pd.DataFrame(records)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
        except FileNotFoundError:
            # Create new file
            print(f"[INFO] Creating new file: {filename}")
            combined_df = pd.DataFrame(records)
        
        # Save to Excel
        combined_df.to_excel(filename, index=False)
        print(f"[SUCCESS] Data saved to {filename}")

def get_core_dumps_output(hostname):
    """
    Get the stored core dumps output for a specific hostname
    """
    return core_dumps_storage.get(hostname, "No core dumps data available")

def collect_metrics():
    """
    Collect metrics from all devices defined in data.json with error handling
    """
    all_results = []
    
    # Use ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_device = {executor.submit(login_and_run_commands, device["name"], device["vm"], device["type"]): device for device in data["devices"]}
        
        for future in as_completed(future_to_device):
            device = future_to_device[future]
            device_name = device["name"]
            
            try:
                version_output, chassis_output, monitoring_output, core_dumps_output, arena_output = future.result()
                
                hostname, model, junos = parse_show_version(version_output)
                routing_engine_desc = parse_chassis_hardware(chassis_output)
                if device["type"] == "spc3":
                    security_data = parse_security_monitoring_spc3(monitoring_output)
                else:
                    security_data = parse_security_monitoring(monitoring_output)
                cores, core_output = parse_system_core_dumps(core_dumps_output)
                global_data_shm = parse_arena(arena_output)
                
                save_to_excel(hostname, model, junos, routing_engine_desc, security_data, cores, global_data_shm, core_output)
                
                all_results.append({
                    "device_name": device_name,
                    "hostname": hostname,
                    "model": model,
                    "junos": junos,
                    "routing_engine_desc": routing_engine_desc,
                    "security_data": security_data,
                    "cores": cores,
                    "global_data_shm": global_data_shm,
                    "status": "success"
                })
                
                print(f"[SUCCESS] Completed processing for {device_name}")
                
            except Exception as e:
                print(f"[ERROR] Failed to process {device_name}: {e}")
                import traceback
                traceback.print_exc()
                
                # Save error to Excel with "File Fetch Failed" for all fields
                error_msg = str(e)
                save_to_excel(
                    hostname=device_name,
                    model=None,
                    junos=None,
                    routing_engine_desc=None,
                    security_data=None,
                    cores="File Fetch Failed",
                    global_data_shm="File Fetch Failed",
                    core_dumps_output=None,
                    error_msg=error_msg
                )
                
                all_results.append({
                    "device_name": device_name,
                    "status": "failed",
                    "error": str(e)
                })
    
    return all_results

def get_latest_metrics(filename="security_monitoring.xlsx"):
    try:
        df = pd.read_excel(filename)
        if df.empty:
            return{"security": []}
        
        # Get the latest entry for each unique hostname
        # Group by Hostname and get the row with max Timestamp for each group
        latest_data = df.sort_values('Timestamp').groupby('Hostname', as_index=False).last()
        
        # Replace NaN and None with appropriate string values for JSON serialization
        latest_data = latest_data.fillna("N/A")
        
        security_data = latest_data.to_dict(orient='records')
        
        # Get the most recent timestamp from all devices
        latest_timestamp = df['Timestamp'].max()
        
        return{"timestamp": str(latest_timestamp),
                "security": security_data
            }
    except Exception as e:
        return {"error": str(e)}

def get_latest_metrics_on_load(filename="security_monitoring.xlsx"):
    """
    Get the latest metrics from Excel file without executing any commands.
    Returns None if file doesn't exist or is empty.
    """
    try:
        if not os.path.exists(filename):
            return None
        
        df = pd.read_excel(filename)
        
        if df.empty:
            return None
        
        # Get the latest entry for each unique hostname
        latest_data = df.sort_values('Timestamp').groupby('Hostname', as_index=False).last()
        
        # Replace NaN and None with appropriate string values
        latest_data = latest_data.fillna("N/A")
        
        # Get the timestamp of the latest entry
        latest_timestamp = df['Timestamp'].max()
        
        # Convert dataframe to list of dictionaries
        records = latest_data.to_dict('records')
        
        return {
            "security": records,
            "timestamp": str(latest_timestamp)
        }
    except Exception as e:
        print(f"[ERROR] Failed to read existing metrics: {e}")
        import traceback
        traceback.print_exc()
        return None

def collect_metrics_by_type(device_type=None):
    """
    Collect metrics for specific device type or all devices.
    device_type can be: 'vsrx', 'highend', 'branch', 'spc3', or None for all
    """
    print("==== Starting Metrics Collection ====")
    
    # Filter devices by type if specified
    devices_to_process = data["devices"]
    if device_type:
        devices_to_process = [d for d in data["devices"] if d["type"] == device_type]
        print(f"[INFO] Processing only {device_type} devices: {[d['name'] for d in devices_to_process]}")
    
    if not devices_to_process:
        print(f"[WARNING] No devices found for type: {device_type}")
        return
    
    # Use ThreadPoolExecutor to connect to devices in parallel
    max_workers = min(5, len(devices_to_process))
    all_results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_device, device): device 
            for device in devices_to_process
        }
        
        for future in as_completed(futures):
            device = futures[future]
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                print(f"[ERROR] Failed to process {device['name']}: {e}")
                all_results.append({
                    "device_name": device['name'],
                    "status": "failed",
                    "error": str(e)
                })
    
    print("==== Metrics Collection Complete ====")
    return all_results

def process_device(device):
    """
    Process a single device - login, run commands, parse and save data
    """
    device_name = device["name"]
    device_vm = device["vm"]
    device_type = device["type"]
    
    try:
        print(f"[INFO] Starting to process {device_name}")
        
        # Login and run commands
        version_output, chassis_output, monitoring_output, core_dumps_output, arena_output = login_and_run_commands(
            device_name, device_vm, device_type
        )
        
        # Parse outputs
        hostname, model, junos = parse_show_version(version_output)
        routing_engine_desc = parse_chassis_hardware(chassis_output)
        
        # Use SPC3-specific parser if device type is spc3
        if device_type == "spc3":
            security_data = parse_security_monitoring_spc3(monitoring_output)
        else:
            security_data = parse_security_monitoring(monitoring_output)
        
        cores, core_output = parse_system_core_dumps(core_dumps_output)
        global_data_shm = parse_arena(arena_output)
        
        # Save to Excel
        save_to_excel(hostname, model, junos, routing_engine_desc, security_data, cores, global_data_shm, core_output)
        
        print(f"[SUCCESS] Completed processing for {device_name}")
        
        return {
            "device_name": device_name,
            "hostname": hostname,
            "status": "success"
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to process {device_name}: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error to Excel with "File Fetch Failed" for all fields
        save_to_excel(
            hostname=device_name,
            model=None,
            junos=None,
            routing_engine_desc=None,
            security_data=None,
            cores="File Fetch Failed",
            global_data_shm="File Fetch Failed",
            core_dumps_output=None,
            error_msg=str(e)
        )
        
        return {
            "device_name": device_name,
            "status": "failed",
            "error": str(e)
        }

# ========== Main Entry ==========
if __name__ == "__main__":
    try:
        # Collect metrics from all devices
        results = collect_metrics()
        
        print("\n" + "=" * 80)
        print("SUMMARY OF ALL DEVICES:")
        print("=" * 80)
        
        for result in results:
            if result["status"] == "success":
                print(f"✓ {result['device_name']} ({result['hostname']}) - SUCCESS")
            else:
                print(f"✗ {result['device_name']} - FAILED: {result.get('error', 'Unknown error')}")
        
        print(f"\n[SUCCESS] Processed {len(results)} device(s)")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
