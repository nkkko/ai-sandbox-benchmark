# providers/modal.py

import time
import logging
from typing import Dict
import modal
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

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
    metrics = EnhancedTimingMetrics()
    sandbox = None
    try:
        logger.info("Creating Modal sandbox...")
        start = time.time()

        # Look up or create an app as required by Modal
        app = modal.App.lookup(
            "sandbox-execution",
            create_if_missing=True
        )

        # Create secrets for environment variables if provided
        secrets = None
        if env_vars:
            env_dict = {k: v for k, v in env_vars.items()}
            secrets = [modal.Secret.from_dict(env_dict)]

        # Create a sandbox with the app and image
        sandbox = modal.Sandbox.create(
            app=app,
            image=image,
            secrets=secrets
        )

        # Write the code to a file inside the sandbox
        logger.info("Writing code to sandbox...")

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

        # Track setup time
        metrics.add_metric("Workspace Creation", time.time() - start)

        # Initialize dependency utilities
        logger.info("Creating dependency utilities in Modal sandbox directly...")
        
        # Check for dependencies
        logger.info("Checking for dependencies in code...")
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
        logger.info(f"Dependency check output: {deps_stdout}")
        if deps_stderr:
            logger.warning(f"Dependency check stderr: {deps_stderr}")
        
        # Execute the code
        logger.info("Running code in Modal sandbox...")
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
            logger.info(f"Stderr from Modal execution: {stderr_data}")

        return output, metrics

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"Modal execution error: {str(e)}")
        raise
    finally:
        # Clean up the sandbox
        if sandbox:
            start_cleanup = time.time()
            sandbox.terminate()
            metrics.add_metric("Cleanup", time.time() - start_cleanup)