import asyncio
import paramiko
import time
import logging
import signal
from functools import wraps
import threading
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
        self._jump_locks: Dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()  # Protects lock dict creation
        self._last_used: Dict[str, float] = {}  # Track last usage time for cleanup
        self._connection_timeout = 600  # 10 minutes - close idle connections

    def get_lock(self, device_hostname: str) -> asyncio.Lock:
        """Get or create an asyncio lock for a device (thread-safe creation)."""
        if device_hostname not in self._locks:
            with self._meta_lock:
                if device_hostname not in self._locks:
                    self._locks[device_hostname] = asyncio.Lock()
        return self._locks[device_hostname]

    def get_jump_lock(self, jump_host: str) -> threading.Lock:
        """Get or create a threading lock for a jump host (thread-safe creation)."""
        if jump_host not in self._jump_locks:
            with self._meta_lock:
                if jump_host not in self._jump_locks:
                    self._jump_locks[jump_host] = threading.Lock()
        return self._jump_locks[jump_host]

    def get_jump_conn(self, device_hostname: str) -> Optional[paramiko.SSHClient]:
        conn = self._jump_conns.get(device_hostname)
        if conn and conn.get_transport() and conn.get_transport().is_active():
            return conn
        return None

    def set_jump_conn(self, device_hostname: str, conn: paramiko.SSHClient):
        self._jump_conns[device_hostname] = conn

    def get_device_shell(self, device_hostname: str) -> Optional[paramiko.Channel]:
        shell = self._shells.get(device_hostname)
        
        # Check if connection exists and is still valid
        if shell and not shell.closed:
            # Check if connection has been idle too long
            last_used = self._last_used.get(device_hostname, 0)
            if time.time() - last_used > self._connection_timeout:
                logger.info(f"[Pool] Connection to {device_hostname} idle for {self._connection_timeout}s, closing...")
                self.remove_device_shell(device_hostname)
                return None
            
            # Verify transport is still active
            conn = self._jump_conns.get(device_hostname)
            if conn and conn.get_transport() and conn.get_transport().is_active():
                return shell
            else:
                logger.info(f"[Pool] Connection to {device_hostname} transport inactive, closing...")
                self.remove_device_shell(device_hostname)
                return None
        
        return None

    def set_device_shell(self, device_hostname: str, shell: paramiko.Channel):
        self._shells[device_hostname] = shell
        self._last_used[device_hostname] = time.time()
    
    def update_last_used(self, device_hostname: str):
        """Update the last used timestamp for a connection"""
        self._last_used[device_hostname] = time.time()

    def remove_device_shell(self, device_hostname: str):
        if device_hostname in self._shells:
            try:
                self._shells[device_hostname].send("exit\n")
                self._shells[device_hostname].close()
            except Exception:
                pass
            del self._shells[device_hostname]
        if device_hostname in self._jump_conns:
            try:
                self._jump_conns[device_hostname].close()
            except Exception:
                pass
            del self._jump_conns[device_hostname]
        if device_hostname in self._last_used:
            del self._last_used[device_hostname]
    
    def cleanup_stale_connections(self):
        """Clean up connections that have been idle too long"""
        current_time = time.time()
        stale_devices = []
        
        for device_hostname, last_used in self._last_used.items():
            if current_time - last_used > self._connection_timeout:
                stale_devices.append(device_hostname)
        
        for device_hostname in stale_devices:
            logger.info(f"[Pool] Cleaning up stale connection to {device_hostname}")
            self.remove_device_shell(device_hostname)
    
    def get_pool_stats(self) -> Dict[str, int]:
        """Get statistics about the connection pool"""
        return {
            "total_connections": len(self._shells),
            "active_connections": sum(1 for shell in self._shells.values() if not shell.closed),
            "jump_connections": len(self._jump_conns)
        }


class SSHService:
    """
    Optimized SSH service using paramiko with connection pooling
    and active prompt detection rather than arbitrary sleep delays.

    Routing modes:
      - "direct": esst-srv2-arm → device (no jump host, fastest)
      - "single-hop": ttbg jump host → device (direct)
      - "double-hop": ttbg jump host → esst-srv2-arm → device
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
        routing: str = "double-hop",
        timeout: int = 120,
    ) -> Dict[str, str]:
        lock = self.pool.get_lock(device_hostname)
        async with lock:
            loop = asyncio.get_event_loop()
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self._execute_commands_sync,
                        device_hostname,
                        device_username,
                        device_password,
                        commands,
                        device_name,
                        routing,
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.error(f"SSH execution timed out after {timeout}s for {device_name}")
                self.pool.remove_device_shell(device_hostname)
                raise Exception(f"SSH execution failed for {device_name}: timed out after {timeout}s")

    def _read_until_prompt(self, shell: paramiko.Channel, timeout: int = 6) -> str:
        """Reads from stdout until common CLI prompts or timeout."""
        output = ""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if shell.recv_ready():
                chunk = shell.recv(65536).decode("utf-8", errors="ignore")
                output += chunk

                # Check recent lines — do NOT rstrip() so we don't match MOTDs ending in `#`
                recent = "\n".join(output.splitlines()[-2:])

                if "continue connecting" in recent.lower() or "yes/no" in recent.lower():
                    break
                if "password:" in recent.lower():
                    break

                # Standard CLI prompts end with "> " or "# " or "% " or "$ "
                # Must be at END of line, not in middle of banner text
                # Real prompts have format: user@host:path$ or root>
                last_line = output.splitlines()[-1] if output.splitlines() else ""
                if last_line.endswith("> ") or last_line.endswith("# ") or last_line.endswith("% ") or last_line.endswith("$ "):
                    # Verify it's a real prompt (has username/hostname, not just banner)
                    stripped = last_line.rstrip("> #%$ ")
                    if stripped and ("@" in stripped or "root" in stripped.lower() or "sshivang" in stripped.lower()):
                        break

                # Some routers send ">" without trailing space — wait briefly then accept
                if last_line.endswith(">") or last_line.endswith("#"):
                    stripped = last_line.rstrip(">#")
                    if stripped and ("@" in stripped or "root" in stripped.lower() or "sshivang" in stripped.lower()):
                        time.sleep(0.1)
                        if shell.recv_ready():
                            continue  # More data coming, keep reading
                        break  # No more data, prompt is complete
            else:
                time.sleep(0.05)  # Short poll to yield thread

        return output

    def _clear_buffer(self, shell: paramiko.Channel):
        """Drain any pending data from the shell buffer."""
        while shell.recv_ready():
            shell.recv(8192)

    def _execute_commands_sync(
        self,
        device_hostname: str,
        device_username: str,
        device_password: str,
        commands: List[Tuple[str, str]],
        device_name: str,
        routing: str = "double-hop",
    ) -> Dict[str, str]:

        shell = self.pool.get_device_shell(device_hostname)
        outputs = {}

        try:
            if not shell:
                print(f"[SSH] Establishing NEW pooled connection to {device_name}")
                
                # Direct mode: Connect directly from esst-srv2-arm to device (no jump host)
                if routing == "direct":
                    print(f"[SSH] Direct connection mode: connecting directly to {device_hostname}...")
                    direct_ssh = paramiko.SSHClient()
                    direct_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    direct_ssh.connect(
                        device_hostname,
                        username=device_username,
                        password=device_password,
                        timeout=15,
                        banner_timeout=15,
                        auth_timeout=15,
                        look_for_keys=False,
                        allow_agent=False,
                    )
                    # Enable SSH keepalive to prevent idle disconnects
                    transport = direct_ssh.get_transport()
                    if transport:
                        transport.set_keepalive(30)
                    self.pool.set_jump_conn(device_hostname, direct_ssh)
                    shell = direct_ssh.invoke_shell()
                    self._read_until_prompt(shell, timeout=10)
                    
                else:
                    # Jump host modes (single-hop or double-hop)
                    jump_ssh = self.pool.get_jump_conn(device_hostname)

                    if not jump_ssh:
                        print(f"[SSH] Connecting to jump host {self.jump_host} for {device_name}...")
                        jump_ssh = paramiko.SSHClient()
                        jump_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        jump_ssh.connect(
                            self.jump_host,
                            username=self.jump_username,
                            password=self.jump_password,
                            timeout=30,
                            banner_timeout=30,
                            auth_timeout=30,
                            look_for_keys=False,
                            allow_agent=False,
                        )
                        # Enable SSH keepalive to prevent idle disconnects
                        transport = jump_ssh.get_transport()
                        if transport:
                            transport.set_keepalive(30)
                        self.pool.set_jump_conn(device_hostname, jump_ssh)

                    shell = jump_ssh.invoke_shell()
                    self._read_until_prompt(shell, timeout=5)

                    # Double-hop: ttbg → esst-srv2-arm → device
                    # Single-hop: ttbg → device (direct)
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
                            # Wait for Ubuntu banner and prompt
                            output = self._read_until_prompt(shell, timeout=15)
                            # Additional wait to ensure we're at the prompt
                            time.sleep(0.3)

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
                        # Wait for device login and prompt
                        output = self._read_until_prompt(shell, timeout=15)
                        # Additional wait to ensure we're at the device prompt
                        time.sleep(0.3)

                print(f"[SSH] Entering CLI mode for {device_name}...")
                self._clear_buffer(shell)
                shell.send("cli\n")
                cli_output = self._read_until_prompt(shell, timeout=5)
                
                # Verify we're in Junos CLI (should see "root>" prompt)
                if "root>" not in cli_output and "root@" in cli_output and "~" in cli_output:
                    # We're still on Linux, not Junos - connection failed
                    raise Exception(f"Failed to reach device {device_name} - still on jump host")

                self._clear_buffer(shell)
                shell.send("set cli screen-length 0\n")
                self._read_until_prompt(shell, timeout=5)

                # Ready — clear and register pooled shell
                self._clear_buffer(shell)
                self.pool.set_device_shell(device_hostname, shell)
                print(f"[SSH] Successfully pooled connection to {device_name}")
            else:
                print(f"[SSH] REUSING pooled connection to {device_name}")
                # Update last used timestamp
                self.pool.update_last_used(device_hostname)
                
                # Verify connection is still responsive with a quick test
                try:
                    self._clear_buffer(shell)
                    shell.send("\n")  # Send newline to test responsiveness
                    test_output = self._read_until_prompt(shell, timeout=3)
                    if not test_output or len(test_output) < 2:
                        # Connection seems dead, remove and reconnect
                        print(f"[SSH] Pooled connection to {device_name} unresponsive, reconnecting...")
                        self.pool.remove_device_shell(device_hostname)
                        # Recursively call to establish new connection
                        return self._execute_commands_sync(
                            device_hostname, device_username, device_password,
                            commands, device_name, routing
                        )
                except Exception as e:
                    print(f"[SSH] Pooled connection test failed for {device_name}: {e}, reconnecting...")
                    self.pool.remove_device_shell(device_hostname)
                    return self._execute_commands_sync(
                        device_hostname, device_username, device_password,
                        commands, device_name, routing
                    )

            for cmd_name, cmd in commands:
                print(f"[SSH] Executing {cmd_name}: {cmd}")

                # Clear buffer before command
                while shell.recv_ready():
                    shell.recv(8192)

                shell.send(f"{cmd}\n")
                wait_timeout = 12 if "arena" in cmd else 10

                out_buffer = ""
                start = time.time()
                last_recv_time = start
                idle_threshold = 0.15  # Wait 150ms of no data before checking prompt

                while time.time() - start < wait_timeout:
                    if shell.recv_ready():
                        chunk = shell.recv(65536).decode("utf-8", errors="ignore")
                        out_buffer += chunk
                        last_recv_time = time.time()
                    else:
                        # Only check for prompt if we've been idle for a bit
                        if time.time() - last_recv_time > idle_threshold:
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
