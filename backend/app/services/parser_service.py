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
        """Parse 'show security monitoring' output for standard devices"""
        if not output or len(output.strip()) < 20:
            return []
        
        parsed_data = []
        for line in output.strip().split('\n'):
            parts = line.strip().split()
            
            if not parts or len(parts) < 8:
                continue
            
            # Skip headers and prompts
            if any(x in line for x in ["FPC", "Flow", "session", ">", "#", "show security"]):
                continue
            
            # Validate data line
            if parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit() and parts[3].isdigit():
                try:
                    parsed_data.append({
                        'cpu': int(parts[2]),
                        'memory': int(parts[3]),
                        'flow_session_current': int(parts[4]),
                        'cp_session_current': int(parts[6]) if len(parts) > 6 else 0
                    })
                except ValueError:
                    continue
        
        return parsed_data
    
    @staticmethod
    def parse_security_monitoring_spc3(output: str) -> List[Dict[str, str]]:
        """Parse 'show security monitoring' output for SPC3 devices"""
        if not output or len(output.strip()) < 20:
            return []
        
        cpu = mem = flow_current = cp_current = None
        
        for line in output.strip().split('\n'):
            parts = line.strip().split()
            
            # Look for FPC 1 PIC 1
            if len(parts) >= 4 and parts[0] == "1" and parts[1] == "1":
                if parts[2].isdigit() and parts[3].isdigit():
                    cpu = int(parts[2])
                    mem = int(parts[3])
            
            # Look for Total Sessions
            if "Total Sessions:" in line or "total sessions:" in line.lower():
                for i, part in enumerate(parts):
                    if "sessions:" in part.lower() and len(parts) > i + 3:
                        try:
                            flow_current = int(parts[i + 1])
                            cp_current = int(parts[i + 3])
                        except ValueError:
                            pass
                        break
        
        if all(v is not None for v in [cpu, mem, flow_current, cp_current]):
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
