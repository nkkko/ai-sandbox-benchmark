# providers/daytona.py

import time, os, asyncio, logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
from metrics import EnhancedTimingMetrics
from providers.utils import extract_imports, check_and_install_dependencies

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
        # Define the list of packages to always install for Daytona
        always_install_packages = ['python-dotenv', 'langchain', 'langchain-openai', 'openai', 'langchain-anthropic', 'anthropic']
        
        # Use the centralized dependency installation utility
        dependency_checker = f"""
import sys
from providers.utils import check_and_install_dependencies

# The code is passed in with triple quotes to handle any internal quotes
installed_packages = check_and_install_dependencies(
    '''{code.replace("'", "\\'")}''',
    always_install={always_install_packages}
)
print(f"Installed packages: {{installed_packages}}")
"""
        await loop.run_in_executor(executor, workspace.process.code_run, dependency_checker)

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