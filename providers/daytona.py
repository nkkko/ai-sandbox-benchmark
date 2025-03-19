# providers/daytona.py

import time
import os
import asyncio
import logging
import json
import base64
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Union, Tuple, Optional
from daytona_sdk import Daytona, DaytonaConfig, CreateSandboxParams
from metrics import BenchmarkTimingMetrics
from providers.utils import extract_imports, check_and_install_dependencies

# Export the list_workspaces function to be callable externally
__all__ = ['execute', 'list_workspaces']

logger = logging.getLogger(__name__)

# Create helper functions to log with provider name prefix
def log_info(message):
    logger.info(f"[Daytona] {message}")

def log_error(message):
    logger.error(f"[Daytona] {message}")

def log_warning(message):
    logger.warning(f"[Daytona] {message}")

def log_debug(message):
    logger.debug(f"[Daytona] {message}")

# Global Daytona client cache - shared across executions
# This prevents creating multiple clients which could cause API contention
_daytona_clients = {}
_daytona_client_lock = asyncio.Lock()

# Global dedicated executor for Daytona operations
# Using a module-level attribute to ensure it persists between calls
# CRITICAL: Force a very small fixed-size dedicated thread pool
# The exact size of 1 is important - it forces serial execution
_daytona_executor = ThreadPoolExecutor(max_workers=1)

# Wait time between API calls to avoid rate limiting issues
API_WAIT_TIME = 0.2  # seconds

async def get_or_create_daytona_client(target_region: str) -> Daytona:
    """Get a cached Daytona client for a specific region or create a new one if needed."""
    global _daytona_clients
    
    # Use a lock to prevent multiple concurrent client creation
    async with _daytona_client_lock:
        if target_region not in _daytona_clients:
            log_info(f"Creating new Daytona client for region {target_region}")
            
            # Check if we should use staging environment
            use_stage = os.getenv("USE_DAYTONA_STAGE", "false").lower() == "true"
            
            # Get API credentials from environment based on environment choice
            if use_stage:
                api_key = str(os.getenv("DAYTONA_STAGE_API_KEY"))
                server_url = str(os.getenv("DAYTONA_STAGE_SERVER_URL", "https://stage.daytona.work/api"))
                log_info(f"Using Daytona staging environment: {server_url}")
            else:
                api_key = str(os.getenv("DAYTONA_API_KEY"))
                server_url = str(os.getenv("DAYTONA_SERVER_URL", "https://app.daytona.io/api"))
            
            if not api_key:
                env_var = "DAYTONA_STAGE_API_KEY" if use_stage else "DAYTONA_API_KEY"
                raise ValueError(f"{env_var} environment variable not set")
            
            # Set environment variables that might affect the SDK's HTTP client
            # Force a more conservative connection behavior
            os.environ["HTTPX_POOL_CONNECTIONS"] = "1"
            os.environ["HTTPX_POOL_KEEPALIVE"] = "5"
            os.environ["HTTPX_POOL_TIMEOUT"] = "1"
                
            # Set up Daytona config and client
            config = DaytonaConfig(
                api_key=api_key,
                server_url=server_url,
                target=target_region
            )
            _daytona_clients[target_region] = Daytona(config=config)
        
        return _daytona_clients[target_region]

async def list_workspaces(target_region: str) -> List:
    """
    List existing workspaces to warm up the Daytona connection pool.
    
    Args:
        target_region: Target region to list workspaces from (e.g., 'eu', 'us')
        
    Returns:
        List of workspace objects
    """
    loop = asyncio.get_running_loop()
    
    # Use the module-level persistent global dedicated executor
    global _daytona_executor
    daytona_executor = _daytona_executor
    
    # Get the semaphore for API rate limiting
    global _api_semaphore
    if not hasattr(execute, '_api_semaphore'):
        execute._api_semaphore = asyncio.Semaphore(1)
    api_semaphore = execute._api_semaphore
    
    try:
        # Get client for this region
        daytona = await get_or_create_daytona_client(target_region)
        
        # Use semaphore to respect API rate limits
        async with api_semaphore:
            log_debug("Acquired API semaphore for listing workspaces")
            
            # List workspaces using the persistent executor
            # This triggers the warm pool preparation on Daytona's side
            workspaces = await loop.run_in_executor(daytona_executor, daytona.list)
            
            # Add a small delay to avoid API rate limiting
            await asyncio.sleep(API_WAIT_TIME)
            
        log_info(f"Listed {len(workspaces)} existing workspaces in {target_region}")
        return workspaces
    except Exception as e:
        log_error(f"Error listing workspaces: {str(e)}")
        return []

async def execute(
    code: Union[str, Dict[str, Any]], 
    executor: ThreadPoolExecutor, 
    target_region: str, 
    env_vars: Dict[str, str] = None,
    image: str = "daytonaio/ai-test:0.2.3"
) -> Tuple[str, BenchmarkTimingMetrics]:
    """
    Execute code in Daytona cloud environment with comprehensive setup.
    
    Args:
        code: String code to execute or dict with 'code' and 'config' keys
        executor: ThreadPoolExecutor for running blocking operations (not used directly)
        target_region: Target region to deploy workspace (e.g., 'eu', 'us')
        env_vars: Dictionary of environment variables to set in the workspace
        image: Container image to use (default: daytonaio/ai-test:0.2.3)
        
    Returns:
        Tuple containing result string and timing metrics
    """
    metrics = BenchmarkTimingMetrics()
    loop = asyncio.get_running_loop()
    workspace = None
    
    # Extract test configuration and code if dictionary format provided
    test_config = {}
    if isinstance(code, dict) and 'code' in code:
        test_config = code.get('config', {})
        code_str = code['code']
    else:
        code_str = str(code)
    
    # Use the module-level persistent global dedicated executor
    # This ensures all operations use the same executor to prevent resource contention
    # and avoid thread pool starvation.
    global _daytona_executor
    daytona_executor = _daytona_executor
    log_debug("Using persistent single-worker Daytona executor")
    
    # Rate limiting semaphore - all Daytona API operations
    # This ensures we don't exceed the API rate limit 
    global _api_semaphore
    if not hasattr(execute, '_api_semaphore'):
        execute._api_semaphore = asyncio.Semaphore(1)
        log_debug("Created Daytona API rate limiting semaphore")
    api_semaphore = execute._api_semaphore
    
    try:
        # List existing workspaces to warm up Daytona's pool
        log_info(f"Warming up Daytona pool in {target_region} region...")
        warm_start = time.time()
        await list_workspaces(target_region)
        metrics.add_metric("Warmup Time", time.time() - warm_start)
        
        # Get or create Daytona client for this region (shared across executions)
        log_info(f"Creating workspace in {target_region} region...")
        
        # Get a cached or new Daytona client with improved HTTP client settings
        daytona = await get_or_create_daytona_client(target_region)
        
        # Configure workspace parameters with improved defaults
        params = CreateSandboxParams(
            image=image,
            language="python"
        )
        
        # Use semaphore to ensure we respect API rate limits
        async with api_semaphore:
            log_debug("Acquired API semaphore for workspace creation")
            
            # Start timing just the actual workspace creation API call
            start = time.time()
            
            # Create workspace using our persistent single-worker executor
            # This prevents thread pool contention when multiple providers execute
            workspace = await loop.run_in_executor(daytona_executor, daytona.create, params)
            
            # Measure actual workspace creation time without API semaphore or rate limiting
            metrics.add_metric("Workspace Creation", time.time() - start)
            
            # Add a small delay to avoid API rate limiting
            await asyncio.sleep(API_WAIT_TIME)
        
        log_info(f"Workspace created: {workspace.id}")

        # Prepare consolidated setup script for dependencies and environment
        setup_code = await prepare_setup_code(code_str, env_vars, test_config)
        
        # Run setup code if needed
        if setup_code.strip():
            log_info("Running workspace setup...")
            setup_start = time.time()
            
            # Use semaphore to ensure we respect API rate limits
            async with api_semaphore:
                log_debug("Acquired API semaphore for setup code execution")
                # Use the same persistent executor for consistency
                setup_response = await loop.run_in_executor(daytona_executor, workspace.process.code_run, setup_code)
                # Add a small delay to avoid API rate limiting
                await asyncio.sleep(API_WAIT_TIME)
                
            setup_time = time.time() - setup_start
            metrics.add_metric("Setup Time", setup_time)
        
            # Log setup output (truncated if very long)
            setup_output = setup_response.result.strip()
            if len(setup_output) > 500:
                log_debug(f"Setup output (truncated): {setup_output[:500]}...")
            else:
                log_debug(f"Setup output: {setup_output}")
        else:
            log_info("No setup needed, skipping setup step")
        
        # Execute the actual code with the same persistent executor
        log_info("Executing code...")
        
        # Use semaphore to ensure we respect API rate limits
        async with api_semaphore:
            log_debug("Acquired API semaphore for code execution")
            
            # Start timing only the actual code execution API call
            start = time.time()
            response = await loop.run_in_executor(daytona_executor, workspace.process.code_run, code_str)
            execution_time = time.time() - start
            
            # Add a small delay to avoid API rate limiting (not part of the timing)
            await asyncio.sleep(API_WAIT_TIME)
            
        log_info(f"Code execution completed in {execution_time:.2f}s (workspace: {workspace.id})")
        metrics.add_metric("Code Execution", execution_time)
        
        # Process response: check for JSON data structures
        result = response.result
        try:
            # If response is valid JSON, parse it for better handling
            json_result = json.loads(result)
            log_info("Response contained valid JSON data")
            
            # Handle image results (like matplotlib outputs)
            if isinstance(json_result, dict) and 'image' in json_result:
                log_info("Response contains image data")
                metrics.add_metadata("contains_image", True)
        except (json.JSONDecodeError, TypeError):
            # Not JSON, proceed with regular string result
            pass
            
        return result, metrics

    except Exception as e:
        log_error(f"Execution error: {str(e)}")
        metrics.add_error(str(e))
        raise

    finally:
        # Clean up resources
        if workspace:
            start = time.time()
            try:
                log_info(f"Cleaning up workspace: {workspace.id}...")
                # Get the same client instance used for creation
                daytona = await get_or_create_daytona_client(target_region)
                
                # Use semaphore to ensure we respect API rate limits
                async with api_semaphore:
                    log_debug("Acquired API semaphore for workspace cleanup")
                    # Use the same persistent executor for cleanup
                    await loop.run_in_executor(daytona_executor, daytona.remove, workspace)
                    # No need for a delay after cleanup as it's typically the last operation
                    
                log_info("Cleanup completed")
                metrics.add_metric("Cleanup", time.time() - start)
            except Exception as e:
                log_error(f"Cleanup error for workspace {workspace.id}: {str(e)}")
                metrics.add_error(f"Cleanup error: {str(e)}")

async def prepare_setup_code(
    code: str, 
    env_vars: Optional[Dict[str, str]], 
    test_config: Dict[str, Any]
) -> str:
    """
    Generate setup code for environment variables and dependencies.
    
    Args:
        code: The Python code to be executed
        env_vars: Dictionary of environment variables
        test_config: Test configuration dictionary
        
    Returns:
        String containing the setup code to run
    """
    setup_code = []
    
    # Set up environment variables if provided
    if env_vars and len(env_vars) > 0:
        log_info("Setting up environment variables...")
        # Add environment setup section
        setup_code.append("# Environment variable setup")
        setup_code.append("import os")
        
        # Log key info without revealing values
        for key, value in env_vars.items():
            if key.endswith("_API_KEY"):
                prefix = value[:5] if len(value) >= 5 else value
                log_info(f"  {key} (length: {len(value)}, prefix: {prefix}...)")
            else:
                log_info(f"  {key} (length: {len(value)})")
        
        # Set environment variables directly
        for key, value in env_vars.items():
            setup_code.append(f'os.environ["{key}"] = """{value}"""')
        
        # Create .env file if API keys are provided (useful for libraries that read from .env)
        api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "AZURE_OPENAI_API_KEY"]
        if any(key in env_vars for key in api_keys):
            log_info("Creating .env file for API keys...")
            env_file_content = "\n".join([f"{key}={value}" for key, value in env_vars.items()])
            setup_code.append("\n# Create .env file for tests that need it")
            setup_code.append(f'with open("/home/daytona/.env", "w") as f:')
            setup_code.append(f'    f.write("""{env_file_content}""")')
            setup_code.append("\n# Install and load dotenv")
            setup_code.append("import subprocess, sys")
            setup_code.append("try:")
            setup_code.append("    from dotenv import load_dotenv")
            setup_code.append("except ImportError:")
            setup_code.append('    print("Installing python-dotenv...")')
            setup_code.append('    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])')
            setup_code.append("    from dotenv import load_dotenv")
            setup_code.append("load_dotenv(override=True)")
    
    # Determine required packages
    required_packages = []
    
    # 1. First priority: packages specified in test config
    if test_config and 'packages' in test_config:
        required_packages.extend(test_config['packages'])
        log_info(f"Using packages from test config: {test_config['packages']}")
    
    # 2. Second priority: detect imports from known categories
    # Detect visualization packages
    if "matplotlib" in code or "plt." in code:
        log_info("Visualization detected, adding matplotlib")
        required_packages.extend(['matplotlib', 'pillow'])
    
    # Detect LLM-related imports
    llm_imports = any(x in code for x in ['langchain', 'openai', 'anthropic'])
    if llm_imports or (env_vars and any(key in env_vars for key in api_keys)):
        log_info("LLM packages needed")
        required_packages.extend([
            'python-dotenv',
            'openai', 
            'anthropic',
            'langchain', 
            'langchain-openai',
            'langchain-anthropic',
        ])
    
    # Detect numeric computation
    if any(x in code for x in ['numpy', 'scipy', 'pandas', 'from scipy import fft']):
        log_info("Numeric/scientific computation detected")
        required_packages.extend(['numpy', 'scipy', 'pandas'])
        
    # Detect psutil usage
    if 'import psutil' in code or 'psutil.' in code:
        log_info("System monitoring detected, adding psutil")
        required_packages.append('psutil')
    
    # Install dependencies if needed
    if required_packages:
        log_info(f"Will install packages: {required_packages}")
        setup_code.append("\n# Package installation")
        setup_code.append("import sys, importlib, subprocess")
        setup_code.append("\ndef ensure_package_installed(package_name):")
        setup_code.append("    try:")
        setup_code.append("        importlib.import_module(package_name.split('==')[0])")
        setup_code.append("        print(f\"Package {package_name} is already available\")")
        setup_code.append("        return False")
        setup_code.append("    except ImportError:")
        setup_code.append("        print(f\"Installing {package_name}...\")")
        setup_code.append("        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-U', package_name])")
        setup_code.append("        return True")
        setup_code.append("\nrequired_packages = " + str(required_packages))
        setup_code.append("installed = []")
        setup_code.append("for pkg in required_packages:")
        setup_code.append("    if ensure_package_installed(pkg):")
        setup_code.append("        installed.append(pkg)")
        setup_code.append("print(f\"Installed packages: {installed}\")")
    
    # Detect if we need to extract additional imports from code
    if "import " in code and not required_packages:
        log_info("Checking for additional imports in code")
        setup_code.append("\n# Extract and install additional imports")
        setup_code.append("import re, sys, importlib, subprocess")
        setup_code.append("\ndef extract_imports(code_str):")
        setup_code.append("    pattern = r'^(?:from|import)\\s+([a-zA-Z0-9_]+)'")
        setup_code.append("    imports = set()")
        setup_code.append("    for line in code_str.split('\\n'):")
        setup_code.append("        match = re.match(pattern, line.strip())")
        setup_code.append("        if match:")
        setup_code.append("            imports.add(match.group(1))")
        setup_code.append("    return imports")
        
        # Add the code string with escaped quotes
        escaped_code = code.replace('"', '\\"').replace("'", "\\'")
        setup_code.append(f"\ncode_str = '''{escaped_code}'''")
        setup_code.append("imports = extract_imports(code_str)")
        
        # Check and install non-standard library imports
        setup_code.append("\ndef is_standard_library(module_name):")
        setup_code.append("    try:")
        setup_code.append("        spec = importlib.util.find_spec(module_name)")
        setup_code.append("        if spec is None:")
        setup_code.append("            return False")
        setup_code.append("        path = getattr(spec, 'origin', '')")
        setup_code.append("        return path and ('site-packages' not in path and 'dist-packages' not in path)")
        setup_code.append("    except (ImportError, AttributeError):")
        setup_code.append("        return False")
        
        setup_code.append("\nimport importlib.util")
        setup_code.append("for module in imports:")
        setup_code.append("    if not is_standard_library(module):")
        setup_code.append("        try:")
        setup_code.append("            importlib.import_module(module)")
        setup_code.append("            print(f\"Module {module} is already installed.\")")
        setup_code.append("        except ImportError:")
        setup_code.append("            print(f\"Installing missing dependency: {module}\")")
        setup_code.append("            subprocess.check_call([sys.executable, '-m', 'pip', 'install', module])")
    
    # Add special handling for FFT tests
    if "from scipy import fft" in code:
        log_info("FFT-specific setup required")
        setup_code.append("\n# FFT test setup")
        setup_code.append("import sys, site")
        setup_code.append("# Ensure site-packages is in the path")
        setup_code.append("site_packages = site.getsitepackages()[0]")
        setup_code.append("if site_packages not in sys.path:")
        setup_code.append("    sys.path.insert(0, site_packages)")
        setup_code.append("# Add user site-packages")
        setup_code.append("user_site = site.getusersitepackages()")
        setup_code.append("if user_site not in sys.path:")
        setup_code.append("    sys.path.append(user_site)")
        setup_code.append("# Verify imports")
        setup_code.append("try:")
        setup_code.append("    import numpy as np")
        setup_code.append("    from scipy import fft")
        setup_code.append("    print(\"Successfully imported numpy and scipy\")")
        setup_code.append("except ImportError as e:")
        setup_code.append("    print(f\"Import error: {e}\")")
        setup_code.append("    print(f\"Python path: {sys.path}\")")
    
    # For visualization support
    if "matplotlib" in code:
        log_info("Adding matplotlib configuration")
        setup_code.append("\n# Configure matplotlib")
        setup_code.append("import matplotlib")
        setup_code.append("matplotlib.use('Agg')  # Use non-interactive backend")
    
    return "\n".join(setup_code)