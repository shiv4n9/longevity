import asyncio
import paramiko
import time
import logging
from typing import Dict, List, Tuple, Optional
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class SSHConnectionPool:
    """Manages persistent paramiko SSH connections to devices through jump hosts."""
    def __init__(self):
        self._jump_conns: Dict[str, paramiko.SSHClient] = {}
        self._shells: Dict[str, paramiko.Channel] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
    
    def get_lock(self, device_hostname: str) -> asyncio.Lock:
        if device_hostname not in self._locks:
            self._locks[device_hostname] = asyncio.Lock()
        return self._locks[device_hostname]
        
    def get_jump_conn(self, jump_host: str) -> Optional[paramiko.SSHClient]:
        conn = self._jump_conns.get(jump_host)
        if conn and conn.get_transport() and conn.get_transport().is_active():
            return conn
        return None
        
    def set_jump_conn(self, jump_host: str, conn: paramiko.SSHClient):
        self._jump_conns[jump_host] = conn
        
    def get_device_shell(self, device_hostname: str) -> Optional[paramiko.Channel]:
        shell = self._shells.get(device_hostname)
        if shell and not shell.closed:
            return shell
        return None
        
    def set_device_shell(self, device_hostname: str, shell: paramiko.Channel):
        self._shells[device_hostname] = shell
        
    def remove_device_shell(self, device_hostname: str):
        if device_hostname in self._shells:
            try:
                self._shells[device_hostname].send("exit\n")
                self._shells[device_hostname].close()
            except:
                pass
            del self._shells[device_hostname]


class SSHService:
    """
    Highly optimized SSH service using paramiko with connection pooling
    and active prompt detection rather than arbitrary sleep delays.
    """
    def __init__(self):
        self.jump_host = settings.jump_host
        self.jump_username = settings.jump_host_username
        self.jump_password = settings.jump_host_password
        self.pool = SSHConnectionPool()
    
    async def execute_commands(
        self,
        device_hostname: str,
        device_username: str,
        device_password: str,
        commands: List[Tuple[str, str]],
        device_name: str,
        routing: str = "double-hop"
    ) -> Dict[str, str]:
        lock = self.pool.get_lock(device_hostname)
        async with lock:
            # Run the synchronous paramiko code in a thread pool to avoid blocking async Event Loop
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self._execute_commands_sync,
                device_hostname,
                device_username,
                device_password,
                commands,
                device_name,
                routing
            )

    def _read_until_prompt(self, shell: paramiko.Channel, timeout: int = 15) -> str:
        """Reads from stdout until common CLI prompts or wait timeout."""
        output = ""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if shell.recv_ready():
                chunk = shell.recv(65536).decode('utf-8', errors='ignore')
                output += chunk
                
                # Check recent lines. Do NOT rstrip() so we don't accidentally match MOTDs that end in `#`
                recent = "\n".join(output.splitlines()[-2:])
                
                if "continue connecting" in recent.lower() or "yes/no" in recent.lower():
                    break
                if "password:" in recent.lower():
                    break
                
                # Check for cli shell prompt usually end with space
                if recent.endswith("> ") or recent.endswith("# ") or recent.endswith("% ") or recent.endswith("$ "):
                    break
                # Some routers might just send the caret without space if buffer cuts
                if recent.endswith(">"):
                    # Wait tiny amount to see if space follows, else break
                    pass
            else:
                time.sleep(0.05) # short poll to yield thread
                
            # Fallback strict check in case it's literally at the end
            if output.endswith("> ") or output.endswith("# "):
                break
        return output

    def _clear_buffer(self, shell: paramiko.Channel):
        while shell.recv_ready():
            shell.recv(8192)

    def _execute_commands_sync(
        self,
        device_hostname: str,
        device_username: str,
        device_password: str,
        commands: List[Tuple[str, str]],
        device_name: str,
        routing: str = "double-hop"
    ) -> Dict[str, str]:
        
        shell = self.pool.get_device_shell(device_hostname)
        outputs = {}
        
        try:
            if not shell:
                print(f"[SSH] Establishing NEW pooled connection to {device_name}")
                jump_ssh = self.pool.get_jump_conn(self.jump_host)
                if not jump_ssh:
                    print(f"[SSH] Connecting to jump host {self.jump_host}...")
                    jump_ssh = paramiko.SSHClient()
                    jump_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    jump_ssh.connect(
                        self.jump_host,
                        username=self.jump_username,
                        password=self.jump_password,
                        timeout=60,
                        banner_timeout=60,
                        auth_timeout=60,
                        look_for_keys=False,
                        allow_agent=False
                    )
                    self.pool.set_jump_conn(self.jump_host, jump_ssh)
                
                shell = jump_ssh.invoke_shell()
                self._read_until_prompt(shell, timeout=5)
                
                if routing == "double-hop":
                    print(f"[SSH] Double-hop: SSHing to esst-srv2-arm...")
                    self._clear_buffer(shell)
                    shell.send("ssh root@esst-srv2-arm\n")
                    output = self._read_until_prompt(shell, timeout=10)
                    
                    if "continue connecting" in output.lower() or "yes/no" in output.lower():
                        self._clear_buffer(shell)
                        shell.send("yes\n")
                        output = self._read_until_prompt(shell, timeout=3)
                        
                    if "password:" in output.lower():
                        self._clear_buffer(shell)
                        shell.send("Embe1mpls\n")
                        output = self._read_until_prompt(shell, timeout=10)
                            
                print(f"[SSH] SSHing to device {device_hostname}...")
                self._clear_buffer(shell)
                shell.send(f"ssh {device_username}@{device_hostname}\n")
                output = self._read_until_prompt(shell, timeout=10)
                
                if "continue connecting" in output.lower() or "yes/no" in output.lower():
                    self._clear_buffer(shell)
                    shell.send("yes\n")
                    output = self._read_until_prompt(shell, timeout=3)
                    
                if "password:" in output.lower():
                    self._clear_buffer(shell)
                    shell.send(f"{device_password}\n")
                    output = self._read_until_prompt(shell, timeout=10)
                
                print(f"[SSH] Entering CLI mode...")
                self._clear_buffer(shell)
                shell.send("cli\n")
                self._read_until_prompt(shell, timeout=5)
                
                self._clear_buffer(shell)
                shell.send("set cli screen-length 0\n")
                self._read_until_prompt(shell, timeout=5)
                
                # Ready! Now clear everything and register
                self._clear_buffer(shell)
                self.pool.set_device_shell(device_hostname, shell)
                print(f"[SSH] Successfully pooled connection to {device_name}")
            else:
                print(f"[SSH] REUSING pooled connection to {device_name}")

            for cmd_name, cmd in commands:
                print(f"[SSH] Executing {cmd_name}: {cmd}")
                
                # Clear standard buffer
                while shell.recv_ready():
                    shell.recv(8192)
                    
                shell.send(f"{cmd}\n")
                wait_timeout = 25 if "arena" in cmd else 15
                
                out_buffer = ""
                start = time.time()
                last_recv_time = start
                idle_threshold = 0.2  # Wait 200ms of no data before checking prompt
                
                while time.time() - start < wait_timeout:
                    if shell.recv_ready():
                        chunk = shell.recv(65536).decode('utf-8', errors='ignore')
                        out_buffer += chunk
                        last_recv_time = time.time()
                    else:
                        # Only check for prompt if we've been idle for a bit
                        if time.time() - last_recv_time > idle_threshold:
                            # Use fast strip check since we are executing clean commands now
                            recent = "\n".join(out_buffer.splitlines()[-2:]).rstrip()
                            if recent.endswith(">") or recent.endswith("#"):
                                break
                        time.sleep(0.05)
                        
                outputs[cmd_name] = out_buffer
                print(f"[SSH] Collected {len(out_buffer)} bytes for {cmd_name}")

            return outputs
            
        except Exception as e:
            print(f"[SSH] Error on {device_name}: {str(e)}")
            self.pool.remove_device_shell(device_hostname)
            raise Exception(f"SSH execution failed for {device_name}: {str(e)}")

ssh_service = SSHService()
