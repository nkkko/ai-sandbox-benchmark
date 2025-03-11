# providers/daytona.py

import time, os, asyncio, logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
from metrics import EnhancedTimingMetrics

logger = logging.getLogger(__name__)

async def execute(code: str, executor: ThreadPoolExecutor, target_region: str, env_vars: Dict[str, str] = None):
    metrics = EnhancedTimingMetrics()
    loop = asyncio.get_running_loop()
    workspace = None
    daytona = None
    try:
        logger.info("Creating Daytona workspace...")
        start = time.time()
        config = DaytonaConfig(
            api_key=str(os.getenv("DAYTONA_API_KEY")),
            server_url=str(os.getenv("DAYTONA_SERVER_URL")),
            target=target_region
        )
        daytona = Daytona(config=config)
        params = CreateWorkspaceParams(language="python")
        workspace = await loop.run_in_executor(executor, daytona.create, params)
        logger.info(f"Workspace created: {workspace.id}")
        metrics.add_metric("Workspace Creation", time.time() - start)

        # Pass environment variables to the workspace
        if env_vars and len(env_vars) > 0:
            logger.info("Environment variables to pass to workspace:")
            for key, value in env_vars.items():
                # Check if key is valid
                if key == "OPENAI_API_KEY":
                    prefix = value[:7] if len(value) >= 7 else value
                    logger.info(f"  {key} (length: {len(value)}, prefix: {prefix}...)")
                else:
                    logger.info(f"  {key} (length: {len(value)})")

            # First create a .env file with all environment variables
            env_file_content = ""
            for key, value in env_vars.items():
                # Just use raw value without quotes to avoid escaping issues
                env_file_content += f"{key}={value}\n"

            create_env_file_code = f"""
with open('/home/daytona/.env', 'w') as f:
    f.write('''{env_file_content}''')
print("Created .env file with environment variables at /home/daytona/.env")

# Create a copy in the current directory as well
with open('.env', 'w') as f:
    f.write('''{env_file_content}''')
print("Created .env file with environment variables in current directory")

# Also load the .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("Installing python-dotenv")
    import sys, subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file after installing python-dotenv")
"""
            logger.info("Creating .env file in Daytona workspace")
            await loop.run_in_executor(
                executor,
                workspace.process.code_run,
                create_env_file_code
            )

            # Also set each environment variable using direct Python code execution as a backup
            for key, value in env_vars.items():
                # Use triple quotes to avoid escaping issues
                env_var_code = f"""
import os
os.environ["{key}"] = \"\"\"
{value}
\"\"\".strip()
print("Set {key} with length", len(os.environ["{key}"]))
"""
                logger.info(f"Setting {key} in Daytona workspace")
                await loop.run_in_executor(
                    executor,
                    workspace.process.code_run,
                    env_var_code
                )

            # Verify all environment variables were set correctly
            verification_code = """
import os
print('Environment variable check:')
try:
    from dotenv import load_dotenv
    print("Re-loading environment variables from .env file for verification")
    load_dotenv(override=True)
except Exception as e:
    print(f"Note: Could not load from .env file: {e}")

# Check if .env file exists and show its contents
try:
    print("\\n.env file contents in current directory:")
    with open('.env', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading .env file in current directory: {e}")

try:
    print("\\n.env file contents in home directory:")
    with open('/home/daytona/.env', 'r') as f:
        print(f.read())
except Exception as e:
    print(f"Error reading .env file in home directory: {e}")

print("\\nEnvironment variables in os.environ:")
"""
            for key in env_vars.keys():
                verification_code += f"""
if "{key}" in os.environ:
    print("{key} is SET with length:", len(os.environ["{key}"]))
else:
    print("{key} is NOT SET")
"""

            await loop.run_in_executor(
                executor,
                workspace.process.code_run,
                verification_code
            )

        # Check and install dependencies
        logger.info("Checking for dependencies in code...")
        dependency_checker = """
import re, sys, subprocess

# First, ensure python-dotenv is installed
try:
    import dotenv
    print("✓ Module 'dotenv' is already installed")
except ImportError:
    print("⚠ Module 'dotenv' not found, installing...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
        print("✓ Successfully installed 'python-dotenv'")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install 'python-dotenv': {str(e)}")

# Also ensure required packages are installed
for required_pkg in ['langchain', 'langchain-openai', 'openai', 'langchain-anthropic', 'anthropic']:
    try:
        module_name = required_pkg.replace('-', '_')
        __import__(module_name)
        print(f"✓ Module '{required_pkg}' is already installed")
    except ImportError:
        print(f"⚠ Module '{required_pkg}' not found, installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", required_pkg])
            print(f"✓ Successfully installed '{required_pkg}'")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install '{required_pkg}': {str(e)}")

def extract_imports(code):
    # Extract all import statements
    import_pattern = re.compile(r'^(?:from|import)\s+([a-zA-Z0-9_]+)', re.MULTILINE)
    return set(import_pattern.findall(code))

def check_and_install_dependencies(code):
    # Get all imports
    imports = extract_imports(code)

    # Skip standard library modules
    std_lib_modules = set(sys.modules.keys()) & imports
    third_party_modules = imports - std_lib_modules

    for module in third_party_modules:
        try:
            __import__(module)
            print(f"✓ Module '{module}' is already installed")
        except ImportError:
            print(f"⚠ Module '{module}' not found, installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", module])
                print(f"✓ Successfully installed '{module}'")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to install '{module}': {str(e)}")

# The code string is passed in quotes to the function
check_and_install_dependencies('''{code_str}''')
"""
        # Replace {code_str} with the actual code, escaping any quotes
        dependency_installer = dependency_checker.replace("{code_str}", code.replace("'", "\\'"))
        await loop.run_in_executor(executor, workspace.process.code_run, dependency_installer)

        logger.info("Executing code in Daytona...")
        start = time.time()
        response = await loop.run_in_executor(executor, workspace.process.code_run, code)
        logger.info(f"Code execution completed in workspace {workspace.id}: {response}")
        metrics.add_metric("Code Execution", time.time() - start)
        return response.result, metrics

    except Exception as e:
        metrics.add_error(str(e))
        logger.error(f"Daytona execution error: {str(e)}")
        raise

    finally:
        if workspace and daytona:
            start = time.time()
            try:
                logger.info(f"Cleaning up Daytona workspace: {workspace.id}...")
                await loop.run_in_executor(executor, daytona.remove, workspace)
                logger.info("Daytona cleanup completed")
                metrics.add_metric("Cleanup", time.time() - start)
            except Exception as e:
                logger.error(f"Daytona cleanup error for workspace {workspace.id}: {str(e)}")
                metrics.add_error(f"Cleanup error: {str(e)}")