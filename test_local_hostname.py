#!/usr/bin/env python3
"""Test if devices are reachable via short hostname from esst-srv2-arm"""
import paramiko
import time

def read_until_prompt(shell, timeout=15):
    output = ""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if shell.recv_ready():
            chunk = shell.recv(65536).decode("utf-8", errors="ignore")
            output += chunk
            
            last_line = output.splitlines()[-1] if output.splitlines() else ""
            
            if "continue connecting" in last_line.lower() or "yes/no" in last_line.lower():
                break
            if "password:" in last_line.lower():
                break
            if last_line.endswith("> ") or last_line.endswith("# ") or last_line.endswith("% ") or last_line.endswith("$ "):
                break
            if last_line.endswith(">") or last_line.endswith("#"):
                time.sleep(0.1)
                if not shell.recv_ready():
                    break
        else:
            time.sleep(0.05)
    
    return output

def main():
    # Connect to ttbg-shell012
    print("=== Connecting to ttbg-shell012 ===")
    jump_ssh = paramiko.SSHClient()
    jump_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    jump_ssh.connect(
        "ttbg-shell012.juniper.net",
        username="sshivang",
        password="03Juniper@2026",
        timeout=60,
        look_for_keys=False,
        allow_agent=False,
    )
    
    shell = jump_ssh.invoke_shell()
    output = read_until_prompt(shell, timeout=5)
    
    # SSH to esst-srv2-arm
    print("=== SSHing to esst-srv2-arm ===")
    shell.send("ssh root@esst-srv2-arm\n")
    output = read_until_prompt(shell, timeout=10)
    
    if "continue connecting" in output.lower() or "yes/no" in output.lower():
        shell.send("yes\n")
        output = read_until_prompt(shell, timeout=3)
    
    if "password:" in output.lower():
        shell.send("Embe1mpls\n")
        output = read_until_prompt(shell, timeout=20)
        time.sleep(0.5)
    
    print(f"On esst-srv2-arm: {output.splitlines()[-1]}")
    
    # Try short hostname
    print("\n=== Trying short hostname: snpsrx4100c ===")
    shell.send("ssh root@snpsrx4100c\n")
    output = read_until_prompt(shell, timeout=15)
    print(f"Result: {output.splitlines()[-1]}")
    
    if "password:" in output.lower():
        print("SUCCESS - device is reachable via short hostname!")
        shell.send("Embe1mpls\n")
        output = read_until_prompt(shell, timeout=20)
        time.sleep(0.5)
        print(f"After password: {output.splitlines()[-1]}")
        
        # Enter CLI
        shell.send("cli\n")
        output = read_until_prompt(shell, timeout=5)
        print(f"After CLI: {output.splitlines()[-1]}")
        
        # Test command
        shell.send("show security monitoring\n")
        output = read_until_prompt(shell, timeout=15)
        print(f"\n=== OUTPUT ===\n{output}\n")
    
    shell.close()
    jump_ssh.close()

if __name__ == "__main__":
    main()
