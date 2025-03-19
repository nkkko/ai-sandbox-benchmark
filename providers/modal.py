# providers/modal.py

import time
import logging
from typing import Dict
import modal
from metrics import BenchmarkTimingMetrics

logger = logging.getLogger(__name__)

# Create logging helpers with provider prefix
def log_info(message):
    logger.info(f"[Modal] {message}")

def log_error(message):
    logger.error(f"[Modal] {message}")

def log_warning(message):
    logger.warning(f"[Modal] {message}")

# Define the image with necessary packages at global scope
image = modal.Image.debian_slim().pip_install(
    "numpy", 
    "pandas", 
    "scipy",  # Required for FFT tests
    "matplotlib",
    "requests",
    "psutil"
).add_local_python_source(
    "comparator", 
    "metrics", 
    "tests"
)

# No need for a separate init function - we'll define the dependencies directly in the sandbox


async def execute(code: str, env_vars: Dict[str, str] = None):
    metrics = BenchmarkTimingMetrics()
    sandbox = None
    try:
        log_info("Creating sandbox...")

        # Extract test configuration if available
        test_config = {}
        original_code = code  # Save original code for debugging
        try:
            # Check if we're passed a code_config dictionary directly
            if isinstance(code, dict) and 'code' in code and 'config' in code:
                # New format with config
                test_config = code.get('config', {})
                # Update code to be just the code string
                code = code['code']
                log_info("Extracted code and config from dictionary format")
            else:
                log_info(f"Code is a {type(code)}, not a dictionary with config")
        except Exception as e:
            log_info(f"Error extracting test configuration: {e}")
            # If there's an error, make sure code is a string
            if not isinstance(code, str):
                log_error(f"Code is not a string: {type(code)}")
                code = str(code)  # Force to string to avoid further errors

        # Look up or create an app as required by Modal
        app = modal.App.lookup(
            "sandbox-execution",
            create_if_missing=True
        )

        # Create secrets for environment variables if provided
        secrets = []  # Initialize as empty list, not None
        if env_vars and len(env_vars) > 0:
            log_info(f"Setting environment variables: {list(env_vars.keys())}")
            env_dict = {k: v for k, v in env_vars.items()}
            secrets = [modal.Secret.from_dict(env_dict)]

        # Create a sandbox with the app and image
        log_info("Creating Modal sandbox...")
        start = time.time()
        sandbox = modal.Sandbox.create(
            app=app,
            image=image,
            secrets=secrets  # This will be an empty list if no env vars
        )
        # Track only the actual sandbox creation time
        metrics.add_metric("Workspace Creation", time.time() - start)
        
        # Write the code to a file inside the sandbox
        log_info("Writing code to sandbox...")

        # Create directory and write the code file directly in the sandbox
        mkdir_cmd = sandbox.exec("mkdir", "-p", "/sandbox")
        mkdir_cmd.wait()

        # Write the Python code to a file in the sandbox
        write_cmd = sandbox.exec(
            "bash",
            "-c",
            f'cat > /sandbox/code.py << \'EOL\'\n{code}\nEOL'
        )
        write_cmd.wait()

        # Initialize dependency utilities
        setup_start = time.time()
        log_info("Creating dependency utilities in sandbox directly...")
        
        # Check for dependencies
        log_info("Checking for dependencies in code...")
        dependency_check_code = f"""
import sys, os, re, importlib, subprocess
from typing import List, Set, Dict, Any, Optional

# Create providers directory if needed
if not os.path.exists('providers'):
    os.makedirs('providers')
    with open('providers/__init__.py', 'w') as f:
        f.write('# Package initialization')

# Define utility functions directly
def is_standard_library(module_name: str) -> bool:
    # Standard approach to detect standard library modules
    try:
        path = getattr(importlib.import_module(module_name), "__file__", "")
        return path and ("site-packages" not in path and "dist-packages" not in path)
    except (ImportError, AttributeError):
        # If import fails, we'll assume it's not a standard library
        return False

def extract_imports(code: str) -> Set[str]:
    # This regex pattern captures both 'import x' and 'from x import y' style imports
    pattern = r'^(?:from|import)\\s+([a-zA-Z0-9_]+)'
    imports = set()
    
    for line in code.split('\\n'):
        match = re.match(pattern, line.strip())
        if match:
            imports.add(match.group(1))
    
    return imports

def check_and_install_dependencies(
    code: str,
    provider_context: Optional[Dict[str, Any]] = None,
    always_install: Optional[List[str]] = None
) -> List[str]:
    import subprocess
    
    installed_packages = []
    
    # Install packages that should always be available
    if always_install:
        for package in always_install:
            try:
                importlib.import_module(package)
                print(f"Package {{package}} is already installed.")
            except ImportError:
                print(f"Installing required package: {{package}}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                installed_packages.append(package)
    
    # Extract imports from the code
    imports = extract_imports(code)
    
    # Filter out standard library modules
    third_party_modules = {{
        module for module in imports if not is_standard_library(module)
    }}
    
    # Check each third-party module and install if missing
    for module in third_party_modules:
        try:
            importlib.import_module(module)
            print(f"Module {{module}} is already installed.")
        except ImportError:
            print(f"Installing missing dependency: {{module}}")
            # Use pip to install the package
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])
            installed_packages.append(module)
    
    return installed_packages

# Define common packages needed for tests
always_install_packages = [
    'numpy',  # Required for FFT tests
    'scipy',  # Required for FFT tests
]

# Read the code from file and check dependencies
with open('/sandbox/code.py', 'r') as f:
    code = f.read()
    
installed_packages = check_and_install_dependencies(
    code,
    always_install=always_install_packages
)
print(f"Installed packages: {{installed_packages}}")
"""
        
        # Create the dependency check file
        dependency_check_file = "/sandbox/check_deps.py"
        write_deps_cmd = sandbox.exec(
            "bash",
            "-c",
            f'cat > {dependency_check_file} << \'EOL\'\n{dependency_check_code}\nEOL'
        )
        write_deps_cmd.wait()
        
        # Run the dependency check
        deps_process = sandbox.exec("python", dependency_check_file)
        deps_stdout = deps_process.stdout.read()
        deps_stderr = deps_process.stderr.read()
        log_info(f"Dependency check output: {deps_stdout}")
        if deps_stderr:
            log_warning(f"Dependency check stderr: {deps_stderr}")
        
        # For FFT performance test, ensure packages are properly installed
        if "from scipy import fft" in code:
            log_info("FFT test detected, installing packages directly...")
            pip_install_cmd = sandbox.exec(
                "pip", "install", "--user", "numpy", "scipy"
            )
            # Wait for the installation to complete
            pip_stdout = pip_install_cmd.stdout.read()
            pip_stderr = pip_install_cmd.stderr.read()
            log_info(f"Package installation output: {pip_stdout}")
            if pip_stderr:
                log_warning(f"Package installation stderr: {pip_stderr}")
                
        # Record setup time
        metrics.add_metric("Setup Time", time.time() - setup_start)
            
        # Execute the code
        log_info("Running code in sandbox...")
        start_exec = time.time()
        process = sandbox.exec("python", "/sandbox/code.py")

        # Collect output
        stdout_data = process.stdout.read()
        stderr_data = process.stderr.read()

        # Record execution time
        metrics.add_metric("Code Execution", time.time() - start_exec)

        # Combine outputs if needed
        output = stdout_data
        if stderr_data:
            log_info(f"Stderr from execution: {stderr_data}")

        return output, metrics

    except Exception as e:
        metrics.add_error(str(e))
        log_error(f"Execution error: {str(e)}")
        import traceback
        log_error(f"Exception traceback: {traceback.format_exc()}")
        
        # Still add workspace creation time if available
        if 'start' in locals():
            elapsed = time.time() - start
            if elapsed > 0:
                metrics.add_metric("Workspace Creation", elapsed)
                log_info(f"Workspace creation time (before error): {elapsed:.2f}s")
        
        return f"Error: {str(e)}", metrics
    finally:
        # Clean up the sandbox
        if sandbox:
            start_cleanup = time.time()
            try:
                sandbox.terminate()
                cleanup_time = time.time() - start_cleanup
                metrics.add_metric("Cleanup", cleanup_time)
                log_info(f"Cleanup completed in {cleanup_time:.2f}s")
            except Exception as cleanup_error:
                log_error(f"Error during cleanup: {str(cleanup_error)}")
        log_info("Completed execution")