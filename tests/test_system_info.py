"""
Gather and report essential system information about the sandbox environment.

This test collects detailed information about the system, including OS details,
Python version, CPU, memory, disk space, and environment variables.
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def test_system_info():
    """
    Gather and report essential system information about the sandbox environment.

    Reports:
    - Operating System details
    - Python version and implementation
    - CPU information (cores, model)
    - Memory (RAM) information
    - Disk space information
    - Environment variables
    """
    # Define test configuration
    config = create_test_config(
        env_vars=[],  # No env vars needed
        single_run=True,  # Only need to run once per benchmark session
        packages=["psutil"],  # Try to use psutil if available
        is_info_test=True  # This is an information test, not a performance test
    )

    # Get the sandbox utilities code - we only need package installation
    utils_code = get_sandbox_utils(
        include_timer=False,  # No timing needed for info test
        include_results=False,  # No benchmark results needed
        include_packages=True  # We want to try installing psutil
    )

    # Define the test-specific code
    test_code = """
import os
import sys
import platform
import json
import subprocess
from datetime import datetime

# Try to import psutil, but continue without it if not available
try:
    ensure_packages(["psutil"])
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False
    print("psutil module not available. Some system information will be limited.")

# Function to get system information
def get_system_info():
    info = {}

    # Basic system information
    info["timestamp"] = datetime.now().isoformat()
    info["os"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "architecture": platform.architecture(),
    }

    # Python information
    info["python"] = {
        "version": platform.python_version(),
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "build": platform.python_build(),
    }

    # CPU information
    info["cpu"] = {
        "count_logical": os.cpu_count(),
    }

    # Try to get more detailed CPU info
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                cpuinfo = f.read()
            for line in cpuinfo.split("\\n"):
                if "model name" in line:
                    info["cpu"]["model"] = line.split(":")[1].strip()
                    break
        elif platform.system() == "Darwin":  # macOS
            cpu_model = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
            info["cpu"]["model"] = cpu_model
    except Exception as e:
        info["cpu"]["model"] = f"Error getting CPU model: {str(e)}"

    # Memory information using psutil if available
    if HAS_PSUTIL:
        mem = psutil.virtual_memory()
        info["memory"] = {
            "total": mem.total,
            "available": mem.available,
            "used": mem.used,
            "percent": mem.percent,
        }

        # Disk information
        disk = psutil.disk_usage('/')
        info["disk"] = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
        }
    else:
        info["memory"] = {"error": "psutil not available"}
        info["disk"] = {"error": "psutil not available"}

    # Environment variables (filtered for security)
    safe_env_vars = {
        k: v for k, v in os.environ.items()
        if not any(secret in k.lower() for secret in ["key", "token", "secret", "password", "credential"])
    }
    info["environment"] = safe_env_vars

    return info

# Get and print system information
system_info = get_system_info()

# Format the output for human readability
def format_size(bytes):
    # Convert bytes to human readable format
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} PB"

# Print formatted system information
print("=== System Information ===")
print(f"OS: {system_info['os']['system']} {system_info['os']['release']} ({system_info['os']['platform']})")
print(f"Python: {system_info['python']['version']} ({system_info['python']['implementation']})")
print(f"CPU: {system_info['cpu'].get('model', 'Unknown')} - {system_info['cpu']['count_logical']} logical cores")

if HAS_PSUTIL:
    print(f"Memory: {format_size(system_info['memory']['total'])} total, {system_info['memory']['percent']}% used")
    print(f"Disk: {format_size(system_info['disk']['total'])} total, {system_info['disk']['percent']}% used")
else:
    print("Memory: Information not available (psutil required)")
    print("Disk: Information not available (psutil required)")

print("\\nEnvironment Variables:")
for key, value in sorted(system_info["environment"].items()):
    print(f"  {key}={value}")

# Also output as JSON for programmatic use
print("\\n\\n--- SYSTEM INFO JSON ---")
print(json.dumps(system_info))
print("--- END SYSTEM INFO JSON ---")
"""

    # Combine the utilities and test code
    full_code = f"{utils_code}\n\n{test_code}"

    # Return the test configuration and code
    return {
        "config": config,
        "code": full_code
    }