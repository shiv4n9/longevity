from typing import List, Tuple

class CommandService:
    """Service for device-type specific command generation"""
    
    @staticmethod
    def get_commands_for_device_type(device_type: str) -> List[Tuple[str, str]]:
        """
        Get list of commands for a specific device type.
        Returns list of (command_name, command) tuples.
        """
        base_commands = [
            ("version", "show version | no-more"),
            ("chassis", "show chassis hardware | no-more"),
            ("monitoring", "show security monitoring"),
            ("core_dumps", "show system core-dumps | no-more"),
        ]
        
        if device_type == "vsrx":
            return base_commands + [
                ("arena", 'request pfe execute command "sh arena" target fwdd')
            ]
        elif device_type == "highend":
            return base_commands + [
                ("arena", 'request pfe execute command "sh arena" target fpc0')
            ]
        elif device_type == "branch":
            return base_commands + [
                ("arena", 'request pfe execute command "sh arena" target fwdd')
            ]
        elif device_type == "spc3":
            return base_commands + [
                ("arena", 'request pfe execute command "sh arena" target tnp tnp-name fpc1.pic1')
            ]
        else:
            return base_commands
