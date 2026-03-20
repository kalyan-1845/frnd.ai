import subprocess
import os
import platform
from core.logger import log_event, log_error

def run_command(command: str) -> tuple:
    """
    Executes a shell command and returns (success: bool, output: str).
    Includes safety filters to prevent highly destructive operations.
    """
    if not command:
        return False, "No command provided."

    # Safety Filter
    destructive_patterns = [
        "rm -rf /", "del /f /s /q c:\\windows", "format ", "mkfs", 
        "shutdown", "reboot", "poweroff", ":(){ :|:& };:"
    ]
    
    cmd_lower = command.lower()
    for pattern in destructive_patterns:
        if pattern in cmd_lower:
            return False, f"Safety Block: Command contains a potentially destructive pattern: '{pattern}'"

    log_event("Command Executor", f"Running: {command}")
    
    try:
        # Run command with 30s timeout
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout if result.stdout else result.stderr
        success = result.returncode == 0
        
        if not output.strip():
            output = "Command executed successfully with no output." if success else "Command failed with no output."

        return success, output.strip()

    except subprocess.TimeoutExpired:
        return False, "Command timed out after 30 seconds."
    except Exception as e:
        log_error("Executor.run_command", e)
        return False, f"Execution Error: {str(e)}"

def run_script(script_path: str) -> tuple:
    """Wraps run_command for python scripts specifically."""
    if not os.path.exists(script_path):
        return False, f"File not found: {script_path}"
    
    if script_path.endswith(".py"):
        return run_command(f"python \"{script_path}\"")
    elif script_path.endswith(".js"):
        return run_command(f"node \"{script_path}\"")
    else:
        # Try to execute directly
        return run_command(f"\"{script_path}\"")
