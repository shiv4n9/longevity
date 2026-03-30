import re
from typing import Dict, List, Optional, Tuple

class ParserService:
    """Parser service for extracting metrics from device command outputs"""
    
    @staticmethod
    def parse_show_version(output: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract Hostname, Model, and Junos version from 'show version' output"""
        hostname = model = junos = None
        
        for line in output.strip().split('\n'):
            if "Hostname:" in line:
                hostname = line.split("Hostname:")[1].strip()
            elif "Model:" in line:
                model = line.split("Model:")[1].strip()
            elif "Junos:" in line:
                junos = line.split("Junos:")[1].strip()
        
        return hostname, model, junos
    
    @staticmethod
    def parse_chassis_hardware(output: str) -> Optional[str]:
        """Extract Routing Engine description from 'show chassis hardware' output"""
        for line in output.strip().split('\n'):
            if "Routing Engine" in line:
                parts = re.split(r'\s{2,}', line.strip())
                if parts:
                    return parts[-1]
        return None
    
    @staticmethod
    def parse_security_monitoring(output: str) -> List[Dict[str, str]]:
        """Parse 'show security monitoring' output for standard devices
        
        Handles both numeric values and N/A for CP sessions (common in vSRX)
        Example output:
        FPC PIC CPU Mem   Flow_Current  Flow_Max    CP_Current  CP_Max
         0   0   0  90         0        12582912       N/A        N/A
        """
        if not output or len(output.strip()) < 20:
            return []
        
        parsed_data = []
        for line in output.strip().split('\n'):
            parts = line.strip().split()
            
            if not parts or len(parts) < 5:  # Need at least FPC, PIC, CPU, Mem, Flow
                continue
            
            # Skip headers and prompts
            if any(x in line for x in ["FPC", "Flow", "session", ">", "#", "show security"]):
                continue
            
            # Validate data line - first 4 parts should be digits (FPC, PIC, CPU, Mem)
            if parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit() and parts[3].isdigit():
                try:
                    cpu = int(parts[2])
                    memory = int(parts[3])
                    
                    # Parse flow sessions (parts[4])
                    flow_session_current = None
                    if len(parts) > 4:
                        try:
                            flow_session_current = int(parts[4])
                        except ValueError:
                            pass
                    
                    # Parse CP sessions (parts[6]) - handle N/A
                    cp_session_current = None
                    if len(parts) > 6:
                        try:
                            cp_session_current = int(parts[6])
                        except ValueError:
                            pass
                    
                    parsed_data.append({
                        'cpu': cpu,
                        'memory': memory,
                        'flow_session_current': flow_session_current,
                        'cp_session_current': cp_session_current
                    })
                except ValueError:
                    continue
        
        return parsed_data
    
    @staticmethod
    def parse_security_monitoring_spc3(output: str) -> List[Dict[str, str]]:
        """Parse 'show security monitoring' output for SPC3 devices
        
        For SPC3 devices, we look for PIC 1 data (any FPC with PIC 1)
        Example output:
        FPC PIC CPU Mem        current        maximum        current        maximum
          3   0   0  41              0       13107200              0       15728640
          3   1   0  68              0       26214400              0       31457280
        """
        if not output or len(output.strip()) < 20:
            return []
        
        cpu = mem = flow_current = cp_current = None
        
        for line in output.strip().split('\n'):
            parts = line.strip().split()
            
            # Look for any FPC with PIC 1 (parts[1] == "1")
            # Format: FPC PIC CPU Mem ...
            if len(parts) >= 4:
                # Check if this is a data line (first two parts are digits)
                if parts[0].isdigit() and parts[1].isdigit():
                    # Check if PIC is 1
                    if parts[1] == "1":
                        if parts[2].isdigit() and parts[3].isdigit() and cpu is None:
                            cpu = int(parts[2])
                            mem = int(parts[3])
                            # Get flow sessions from column 4 if available
                            if len(parts) > 4 and parts[4].isdigit():
                                flow_current = int(parts[4])
                            # Get CP sessions from column 6 if available
                            if len(parts) > 6 and parts[6].isdigit():
                                cp_current = int(parts[6])
            
            # Look for Total Sessions line
            if "Total Sessions:" in line or "total sessions:" in line.lower():
                for i, part in enumerate(parts):
                    if "sessions:" in part.lower() and len(parts) > i + 3:
                        try:
                            # If we haven't found flow/cp sessions yet, use Total Sessions
                            if flow_current is None:
                                flow_current = int(parts[i + 1])
                            if cp_current is None:
                                cp_current = int(parts[i + 3])
                        except ValueError:
                            pass
                        break
        
        # Return data if we have at least CPU and memory
        if cpu is not None and mem is not None:
            return [{
                'cpu': cpu,
                'memory': mem,
                'flow_session_current': flow_current,
                'cp_session_current': cp_current
            }]
        
        return []
    
    @staticmethod
    def parse_arena(output: str) -> int:
        """Extract Global Data SHM percentage from 'sh arena' output"""
        for line in output.strip().split('\n'):
            if "global data shm" in line.lower():
                parts = re.split(r'\s+', line.strip())
                for i, part in enumerate(parts):
                    if part.lower() == "global" and i > 0:
                        try:
                            return int(parts[i - 1])
                        except ValueError:
                            pass
        return 0
    
    @staticmethod
    def parse_system_core_dumps(output: str) -> Tuple[bool, str]:
        """Check if core dumps exist and return full output"""
        cores_found = False
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            
            # Skip non-core lines
            if any(x in line for x in ["No such file", "total blocks:", "total files:", "show system", ">", "#"]):
                continue
            
            if line.strip().endswith(':'):
                continue
            
            if "core" in line.lower():
                cores_found = True
                break
        
        return cores_found, output
