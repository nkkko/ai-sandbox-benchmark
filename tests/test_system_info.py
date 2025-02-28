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
    # Mark this test as an info test (not performance focused)
    test_system_info.is_info_test = True
    return """
import os
import sys
import platform
import json
import subprocess
from datetime import datetime

# Try to import psutil, but continue without it if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("psutil module not available. Some system information will be limited.")
    # Try to install psutil if pip is available
    try:
        print("Attempting to install psutil...")
        import pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
        HAS_PSUTIL = True
        print("Successfully installed psutil!")
    except Exception as e:
        print(f"Could not install psutil: {e}")
        pass

# Function to safely execute shell commands and capture output
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except Exception as e:
        return f"Command failed: {str(e)}"

# Get current timestamp
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Collect system information
system_info = {
    "timestamp": timestamp,
    "platform": {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "platform": platform.platform(),
        "uname": platform.uname()._asdict() if hasattr(platform.uname(), '_asdict') else str(platform.uname()),
        "libc_ver": platform.libc_ver()
    },
    "python": {
        "version": sys.version,
        "version_info": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
        },
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "build": platform.python_build()
    }
}

# Get CPU info
try:
    # Start with basic CPU info
    system_info["cpu"] = {}
    
    # Try to get CPU model from /proc/cpuinfo (Linux)
    if os.path.exists('/proc/cpuinfo'):
        cpu_info = run_command("grep 'model name' /proc/cpuinfo | head -1")
        if cpu_info and ":" in cpu_info:
            system_info["cpu"]["model"] = cpu_info.split(":", 1)[1].strip()
    
    # Get load average on Unix systems
    if hasattr(os, 'getloadavg'):
        system_info["cpu"]["load_avg"] = os.getloadavg()
    
    # Use psutil for more detailed CPU info if available
    if HAS_PSUTIL:
        system_info["cpu"].update({
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "cpu_percent": psutil.cpu_percent(interval=1, percpu=False),
            "cpu_freq": {
                "current": getattr(psutil.cpu_freq(), "current", None),
                "min": getattr(psutil.cpu_freq(), "min", None),
                "max": getattr(psutil.cpu_freq(), "max", None)
            }
        })
    else:
        # Fallback to system commands when psutil is not available
        try:
            # Try to get CPU count using nproc command (Linux/Unix)
            cores = run_command("nproc")
            if cores.isdigit():
                system_info["cpu"]["logical_cores"] = int(cores)
            
            # Try to get physical cores (may not be accurate on all systems)
            phys_cores = run_command("grep -c ^processor /proc/cpuinfo")
            if phys_cores.isdigit():
                system_info["cpu"]["physical_cores"] = int(phys_cores)
        except Exception:
            pass
        
except Exception as e:
    system_info["cpu"] = {"error": f"Failed to get CPU info: {str(e)}"}

# Get memory info
try:
    if HAS_PSUTIL:
        # Use psutil for accurate memory info
        memory = psutil.virtual_memory()
        system_info["memory"] = {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free,
            "percent": memory.percent,
            "formatted": {
                "total": f"{memory.total / (1024 ** 3):.2f} GB",
                "available": f"{memory.available / (1024 ** 3):.2f} GB",
                "used": f"{memory.used / (1024 ** 3):.2f} GB",
                "free": f"{memory.free / (1024 ** 3):.2f} GB"
            }
        }
        
        # Get swap info
        swap = psutil.swap_memory()
        system_info["swap"] = {
            "total": swap.total,
            "used": swap.used,
            "free": swap.free,
            "percent": swap.percent,
            "formatted": {
                "total": f"{swap.total / (1024 ** 3):.2f} GB",
                "used": f"{swap.used / (1024 ** 3):.2f} GB",
                "free": f"{swap.free / (1024 ** 3):.2f} GB"
            }
        }
    else:
        # Fallback to system commands when psutil is not available
        try:
            # Try to get memory info from /proc/meminfo (Linux)
            if os.path.exists('/proc/meminfo'):
                mem_info = run_command("cat /proc/meminfo")
                system_info["memory"] = {"raw": mem_info}
                
                # Parse memory info
                mem_total = None
                mem_free = None
                mem_available = None
                
                for line in mem_info.split('\\n'):
                    if 'MemTotal' in line:
                        mem_total = int(line.split()[1]) * 1024  # Convert kB to bytes
                    elif 'MemFree' in line:
                        mem_free = int(line.split()[1]) * 1024
                    elif 'MemAvailable' in line:
                        mem_available = int(line.split()[1]) * 1024
                
                if mem_total:
                    system_info["memory"]["total"] = mem_total
                    system_info["memory"]["formatted"] = {"total": f"{mem_total / (1024 ** 3):.2f} GB"}
                    
                    if mem_free:
                        system_info["memory"]["free"] = mem_free
                        system_info["memory"]["formatted"]["free"] = f"{mem_free / (1024 ** 3):.2f} GB"
                        
                    if mem_available:
                        system_info["memory"]["available"] = mem_available
                        system_info["memory"]["formatted"]["available"] = f"{mem_available / (1024 ** 3):.2f} GB"
                        
                    if mem_total and mem_free:
                        used = mem_total - mem_free
                        system_info["memory"]["used"] = used
                        system_info["memory"]["formatted"]["used"] = f"{used / (1024 ** 3):.2f} GB"
                        system_info["memory"]["percent"] = int((used / mem_total) * 100)
            else:
                # Try free command as another fallback
                free_output = run_command("free -b")
                if free_output:
                    system_info["memory"]["raw"] = free_output
                    
                    # Simple parsing of free output
                    lines = free_output.strip().split('\\n')
                    if len(lines) >= 2:
                        mem_parts = lines[1].split()
                        if len(mem_parts) >= 4:
                            total = int(mem_parts[1])
                            used = int(mem_parts[2])
                            free = int(mem_parts[3])
                            
                            system_info["memory"]["total"] = total
                            system_info["memory"]["used"] = used
                            system_info["memory"]["free"] = free
                            system_info["memory"]["percent"] = int((used / total) * 100) if total > 0 else 0
                            
                            system_info["memory"]["formatted"] = {
                                "total": f"{total / (1024 ** 3):.2f} GB",
                                "used": f"{used / (1024 ** 3):.2f} GB",
                                "free": f"{free / (1024 ** 3):.2f} GB"
                            }
        except Exception as e:
            system_info["memory"]["error"] = f"Failed to parse memory info: {str(e)}"
except Exception as e:
    system_info["memory"] = {"error": f"Failed to get memory info: {str(e)}"}

# Get disk info
try:
    if HAS_PSUTIL:
        # Use psutil for accurate disk info
        disk = psutil.disk_usage('/')
        system_info["disk"] = {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "formatted": {
                "total": f"{disk.total / (1024 ** 3):.2f} GB",
                "used": f"{disk.used / (1024 ** 3):.2f} GB",
                "free": f"{disk.free / (1024 ** 3):.2f} GB"
            }
        }
        
        # Get disk partitions
        system_info["partitions"] = []
        for part in psutil.disk_partitions():
            partition = {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts
            }
            
            # Get usage for each partition if possible
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partition["usage"] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "formatted": {
                        "total": f"{usage.total / (1024 ** 3):.2f} GB",
                        "used": f"{usage.used / (1024 ** 3):.2f} GB",
                        "free": f"{usage.free / (1024 ** 3):.2f} GB"
                    }
                }
            except:
                pass
                
            system_info["partitions"].append(partition)
    else:
        # Fallback to system commands when psutil is not available
        try:
            # Try df command for disk info (works on Linux/Unix/macOS)
            df_output = run_command("df -h /")
            system_info["disk"] = {"raw": df_output}
            
            lines = df_output.strip().split('\\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    # Usually df outputs: Filesystem Size Used Avail Use% Mounted on
                    # But format can vary by system, so be flexible
                    
                    # Try to find size, used and available columns
                    size = None
                    used = None
                    avail = None
                    percent = None
                    
                    # Find values with size units (assume they're the size columns)
                    for i, part in enumerate(parts):
                        if 'G' in part or 'T' in part or 'M' in part:
                            # We found a size column, try to interpret the three main columns
                            if i <= len(parts) - 3:
                                try:
                                    # Get values (handle potential % sign)
                                    size_str = parts[i].replace('G', '').replace('T', '').replace('M', '')
                                    used_str = parts[i+1].replace('G', '').replace('T', '').replace('M', '')
                                    avail_str = parts[i+2].replace('G', '').replace('T', '').replace('M', '')
                                    
                                    # Try to parse and convert to bytes (approximate)
                                    if 'G' in parts[i]:
                                        size = float(size_str) * (1024 ** 3)
                                    elif 'T' in parts[i]:
                                        size = float(size_str) * (1024 ** 4)
                                    elif 'M' in parts[i]:
                                        size = float(size_str) * (1024 ** 2)
                                    
                                    if 'G' in parts[i+1]:
                                        used = float(used_str) * (1024 ** 3)
                                    elif 'T' in parts[i+1]:
                                        used = float(used_str) * (1024 ** 4)
                                    elif 'M' in parts[i+1]:
                                        used = float(used_str) * (1024 ** 2)
                                    
                                    if 'G' in parts[i+2]:
                                        avail = float(avail_str) * (1024 ** 3)
                                    elif 'T' in parts[i+2]:
                                        avail = float(avail_str) * (1024 ** 4)
                                    elif 'M' in parts[i+2]:
                                        avail = float(avail_str) * (1024 ** 2)
                                    
                                    # Look for percent in the next column
                                    if i+3 < len(parts) and '%' in parts[i+3]:
                                        percent = int(parts[i+3].replace('%', ''))
                                    break
                                except:
                                    continue
                    
                    if size is not None:
                        system_info["disk"]["total"] = size
                        system_info["disk"]["formatted"] = {"total": f"{size / (1024 ** 3):.2f} GB"}
                        
                        if used is not None:
                            system_info["disk"]["used"] = used
                            system_info["disk"]["formatted"]["used"] = f"{used / (1024 ** 3):.2f} GB"
                        
                        if avail is not None:
                            system_info["disk"]["free"] = avail
                            system_info["disk"]["formatted"]["free"] = f"{avail / (1024 ** 3):.2f} GB"
                        
                        if percent is not None:
                            system_info["disk"]["percent"] = percent
            
            # Try to get partition info using mount command
            mount_output = run_command("mount")
            if mount_output:
                system_info["partitions"] = []
                for line in mount_output.split('\\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 5:
                            partition = {
                                "device": parts[0],
                                "mountpoint": parts[2],
                                "fstype": parts[4],
                                "raw": line
                            }
                            system_info["partitions"].append(partition)
        except Exception as e:
            system_info["disk"] = {"error": f"Failed to get disk info: {str(e)}"} 
except Exception as e:
    system_info["disk"] = {"error": f"Failed to get disk info: {str(e)}"}

# Get network info (limited)
try:
    if HAS_PSUTIL:
        system_info["network"] = {
            "interfaces": list(psutil.net_if_addrs().keys()),
            "stats": {name: stats._asdict() for name, stats in psutil.net_if_stats().items()}
        }
    else:
        # Fallback to system commands
        try:
            # Try to get network interfaces
            interfaces_output = run_command("ip -o link show")
            if not interfaces_output:
                interfaces_output = run_command("ifconfig -l")  # macOS/BSD fallback
            
            system_info["network"] = {"raw": interfaces_output}
            
            if interfaces_output:
                # Try to parse interfaces
                interfaces = []
                
                # Different parsing for different commands
                if "link show" in interfaces_output:
                    # ip command output
                    for line in interfaces_output.split('\\n'):
                        parts = line.split()
                        if len(parts) >= 2:
                            # Format: NUM: INTERFACE: details
                            interface = parts[1].rstrip(':')
                            interfaces.append(interface)
                else:
                    # ifconfig output (simpler, just a list)
                    interfaces = interfaces_output.split()
                
                system_info["network"]["interfaces"] = interfaces
                
                # Get more detailed info on each interface
                system_info["network"]["details"] = {}
                for interface in interfaces:
                    # Try to get IP address
                    ip_output = run_command(f"ip -4 -o addr show {interface}")
                    if ip_output:
                        for detail_line in ip_output.split('\\n'):
                            if "inet" in detail_line:
                                system_info["network"]["details"][interface] = {"ip_info": detail_line.strip()}
                                break
        except Exception as e:
            system_info["network"] = {"error": f"Failed to get network info: {str(e)}"}
except Exception as e:
    system_info["network"] = {"error": f"Failed to get network info: {str(e)}"}

# Environment variables (filtering out sensitive information)
system_info["env"] = {}
for key, value in os.environ.items():
    # Skip environment variables that might contain sensitive information
    if any(filter_key in key.lower() for filter_key in ['token', 'key', 'passw', 'secret', 'auth']):
        system_info["env"][key] = "<filtered>"
    else:
        system_info["env"][key] = value

# Pretty print the results
print("\\n========================== SYSTEM INFORMATION ==========================\\n")
print(json.dumps(system_info, indent=2, default=str))
print("\\n=======================================================================\\n")

# Also output a human-readable summary
print("\\n======================= SYSTEM SUMMARY =======================")
print(f"Timestamp: {system_info['timestamp']}")

# OS info - should always be available from platform module
try:
    print(f"OS: {system_info['platform']['system']} {system_info['platform']['release']} {system_info['platform']['version']} ({system_info['platform']['architecture']})")
except:
    print("OS: Information not available")

# Python info - should always be available
try:
    print(f"Python: {system_info['python']['version_info']['major']}.{system_info['python']['version_info']['minor']}.{system_info['python']['version_info']['micro']} ({system_info['python']['implementation']})")
except:
    print(f"Python: {sys.version}")

# CPU info - might be missing without psutil
if "error" not in system_info.get("cpu", {}):
    try:
        # Print what's available
        cpu_info = []
        
        if "physical_cores" in system_info["cpu"]:
            cpu_info.append(f"{system_info['cpu']['physical_cores']} physical cores")
            
        if "logical_cores" in system_info["cpu"]:
            cpu_info.append(f"{system_info['cpu']['logical_cores']} logical cores")
            
        if cpu_info:
            print(f"CPU: {', '.join(cpu_info)}")
        else:
            print("CPU: Information available but details limited")
            
        if "model" in system_info["cpu"]:
            print(f"CPU Model: {system_info['cpu']['model']}")
    except:
        print("CPU: Partial information available (see detailed output)")
else:
    print("CPU: Information not available")

# Memory info - might be missing without psutil
if "error" not in system_info.get("memory", {}):
    try:
        memory_parts = []
        
        if "formatted" in system_info["memory"]:
            if "total" in system_info["memory"]["formatted"]:
                memory_parts.append(f"{system_info['memory']['formatted']['total']} total")
                
            if "available" in system_info["memory"]["formatted"]:
                memory_parts.append(f"{system_info['memory']['formatted']['available']} available")
            elif "free" in system_info["memory"]["formatted"]:
                memory_parts.append(f"{system_info['memory']['formatted']['free']} free")
                
            if "percent" in system_info["memory"]:
                memory_parts.append(f"({system_info['memory']['percent']}% used)")
                
        if memory_parts:
            print(f"Memory: {' '.join(memory_parts)}")
        else:
            print("Memory: Information available but details limited")
    except:
        print("Memory: Partial information available (see detailed output)")
else:
    print("Memory: Information not available")

# Disk info - might be missing without psutil
if "error" not in system_info.get("disk", {}):
    try:
        disk_parts = []
        
        if "formatted" in system_info["disk"]:
            if "total" in system_info["disk"]["formatted"]:
                disk_parts.append(f"{system_info['disk']['formatted']['total']} total")
                
            if "free" in system_info["disk"]["formatted"]:
                disk_parts.append(f"{system_info['disk']['formatted']['free']} free")
                
            if "percent" in system_info["disk"]:
                disk_parts.append(f"({system_info['disk']['percent']}% used)")
                
        if disk_parts:
            print(f"Disk: {' '.join(disk_parts)}")
        else:
            print("Disk: Information available but details limited")
    except:
        print("Disk: Partial information available (see detailed output)")
else:
    print("Disk: Information not available")

# Network interfaces summary
if "error" not in system_info.get("network", {}):
    try:
        if "interfaces" in system_info["network"] and system_info["network"]["interfaces"]:
            print(f"Network: {len(system_info['network']['interfaces'])} interfaces: {', '.join(system_info['network']['interfaces'])}")
        else:
            print("Network: Information available but details limited")
    except:
        print("Network: Partial information available (see detailed output)")
else:
    print("Network: Information not available")

# If psutil was available or not
print(f"psutil module: {'Available' if HAS_PSUTIL else 'Not available'}")

# Extra warning if psutil wasn't available
if not HAS_PSUTIL:
    print("NOTE: For more complete system information, install psutil package")

print("=================================================================\\n")
"""