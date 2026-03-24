import asyncio
import asyncssh
from typing import Dict, Optional, Tuple, List
from app.core.config import get_settings

settings = get_settings()

class SSHService:
    """
    SSH service for executing commands on network devices via jump host.
    Replicates legacy Longevity.py login_and_run_commands() logic with async.
    """
    
    def __init__(self):
        self.jump_host = settings.jump_host
        self.jump_username = settings.jump_host_username
        self.jump_password = settings.jump_host_password
    
    async def execute_commands(
        self,
        device_hostname: str,
        device_username: str,
        device_password: str,
        commands: List[Tuple[str, str]],
        device_name: str
    ) -> Dict[str, str]:
        """
        Execute commands on a device through jump host.
        Based on legacy login_and_run_commands() function.
        
        Args:
            device_hostname: Target device hostname (e.g., snpsrx4100c.englab.juniper.net)
            device_username: SSH username for device
            device_password: SSH password for device
            commands: List of (command_name, command) tuples
            device_name: Device name for logging
            
        Returns:
            Dict mapping command names to their outputs
        """
        outputs = {}
        
        try:
            print(f"[SSH] Connecting to jump host {self.jump_host}...")
            print(f"[SSH] Using credentials: {self.jump_username}@{self.jump_host}")
            
            # Step 1: Connect to jump host (ttbg-shell012) with timeout
            try:
                jump_conn = await asyncio.wait_for(
                    asyncssh.connect(
                        self.jump_host,
                        username=self.jump_username,
                        password=self.jump_password,
                        known_hosts=None,
                        connect_timeout=40,
                        server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-dss'],
                        encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-cbc', 'aes192-cbc', 'aes256-cbc', '3des-cbc'],
                        kex_algs=['diffie-hellman-group-exchange-sha256', 'diffie-hellman-group-exchange-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group1-sha1'],
                        mac_algs=['hmac-sha2-256', 'hmac-sha2-512', 'hmac-sha1']
                    ),
                    timeout=60
                )
                print(f"[SSH] Successfully connected to jump host")
            except asyncio.TimeoutError:
                raise Exception(f"Timeout connecting to jump host {self.jump_host}")
            except Exception as e:
                raise Exception(f"Failed to connect to jump host {self.jump_host}: {str(e)}")
            
            print(f"[SSH] Connected to jump host, creating shell session...")
            
            # Step 2: Create interactive shell session
            async with jump_conn.create_process() as process:
                # Clear initial output
                await asyncio.sleep(2)
                try:
                    await asyncio.wait_for(process.stdout.read(65536), timeout=1)
                except:
                    pass
                
                # Step 3: SSH from jump host to target device
                print(f"[SSH] SSHing to device {device_hostname}...")
                process.stdin.write(f"ssh {device_username}@{device_hostname}\n")
                
                # Handle SSH prompts
                login_output = ""
                for _ in range(15):  # 30 seconds timeout
                    await asyncio.sleep(2)
                    try:
                        chunk = await asyncio.wait_for(process.stdout.read(65536), timeout=1)
                        login_output += chunk
                        
                        if "continue connecting" in login_output.lower() or "yes/no" in login_output.lower():
                            print(f"[SSH] Accepting SSH key...")
                            process.stdin.write("yes\n")
                        elif "password:" in login_output.lower():
                            print(f"[SSH] Entering password...")
                            process.stdin.write(f"{device_password}\n")
                            await asyncio.sleep(3)
                        elif "#" in login_output or "~" in login_output:
                            if device_name.split('.')[0] in login_output:
                                print(f"[SSH] Logged into {device_name}")
                                break
                    except asyncio.TimeoutError:
                        continue
                
                # Step 4: Enter CLI mode
                print(f"[SSH] Entering CLI mode...")
                process.stdin.write("cli\n")
                await asyncio.sleep(3)
                
                # Clear CLI output
                try:
                    await asyncio.wait_for(process.stdout.read(65536), timeout=1)
                except:
                    pass
                
                # Step 5: Execute commands
                for cmd_name, cmd in commands:
                    print(f"[SSH] Executing: {cmd}")
                    process.stdin.write(f"{cmd}\n")
                    
                    # Wait based on command type
                    wait_time = 15 if "arena" in cmd else 8 if "core-dumps" in cmd else 5
                    await asyncio.sleep(wait_time)
                    
                    # Collect output in chunks (like legacy script)
                    output = ""
                    iterations = 8 if "arena" in cmd else 5
                    for i in range(iterations):
                        try:
                            # Read with timeout
                            chunk = await asyncio.wait_for(process.stdout.read(4096), timeout=1)
                            if chunk:
                                output += chunk
                                print(f"[SSH] Read {len(chunk)} bytes (iteration {i+1}/{iterations})")
                        except asyncio.TimeoutError:
                            # No data available, continue
                            pass
                        await asyncio.sleep(2 if "arena" in cmd else 1)
                    
                    # For arena command, wait longer if no output yet
                    if "arena" in cmd and len(output.strip()) < 50:
                        print(f"[SSH] Arena: waiting for delayed output...")
                        await asyncio.sleep(10)
                        for i in range(5):
                            try:
                                chunk = await asyncio.wait_for(process.stdout.read(4096), timeout=1)
                                if chunk:
                                    output += chunk
                            except asyncio.TimeoutError:
                                pass
                            await asyncio.sleep(2)
                    
                    outputs[cmd_name] = output
                    print(f"[SSH] Collected {len(output)} bytes for {cmd_name}")
                
                # Step 6: Exit
                process.stdin.write("exit\n")
                await asyncio.sleep(1)
                process.stdin.write("exit\n")
                await asyncio.sleep(1)
            
            jump_conn.close()
            await jump_conn.wait_closed()
            print(f"[SSH] Connection closed for {device_name}")
            
        except Exception as e:
            raise Exception(f"SSH execution failed for {device_name}: {str(e)}")
        
        return outputs

# Global SSH service instance
ssh_service = SSHService()
