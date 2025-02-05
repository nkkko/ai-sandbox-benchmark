from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
import os
from dotenv import load_dotenv
import time
from termcolor import colored
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

def print_timing(description: str, elapsed_time: float):
    """Print timing information in color."""
    elapsed_ms = elapsed_time * 1000  # Convert to milliseconds
    print(colored(
        f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {description}: {elapsed_ms:.2f} ms",
        'cyan'
    ))

def print_status(message: str, status: str = 'info'):
    """Print status messages in different colors based on type."""
    colors = {
        'info': 'blue',
        'success': 'green',
        'error': 'red',
        'warning': 'yellow'
    }
    print(colored(
        f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {message}",
        colors.get(status, 'white')
    ))

def print_code(code: str):
    """Print code with syntax highlighting."""
    print("\n" + colored("Generated Code:", 'yellow', attrs=['bold']))
    print(colored("-" * 80, 'yellow'))
    print(colored(code, 'white'))
    print(colored("-" * 80, 'yellow') + "\n")

# Environment variable checks
start_time = time.time()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables")
if not os.getenv("DAYTONA_API_KEY"):
    raise ValueError("DAYTONA_API_KEY not found in environment variables")
if not os.getenv("DAYTONA_SERVER_URL"):
    raise ValueError("DAYTONA_SERVER_URL not found in environment variables")

daytona_api_key = os.getenv("DAYTONA_API_KEY")
daytona_server_url = os.getenv("DAYTONA_SERVER_URL")
print(daytona_api_key)

if not daytona_api_key or not daytona_server_url:
    raise ValueError("Missing required environment variables")

env_check_time = time.time() - start_time
print_timing("Environment setup completed", env_check_time)

# Create a prompt template for code generation
code_generation_prompt = PromptTemplate(
    input_variables=["language", "task"],
    template="""
You are an expert {language} developer. Write clean, efficient, and well-documented code for the following task:

Task: {task}

Please provide:
1. a complete implementation
2. with no comments
3. always print the output

Code:
"""
)

# Initialize the LLM
start_time = time.time()
llm = OpenAI(
    temperature=0.2,
    max_tokens=1000
)
llm_init_time = time.time() - start_time
print_timing("LLM initialization", llm_init_time)

# Create the code generation chain
code_chain = code_generation_prompt | llm

def generate_code(language: str, task: str):
    """Generate code for a given task in the specified programming language."""
    print_status(f"Generating code for task: {task}", 'info')
    start_time = time.time()
    result = code_chain.invoke({
        "language": language,
        "task": task
    })
    generation_time = time.time() - start_time
    print_timing("Code generation", generation_time)
    return result

def execute_in_sandbox(code: str):
    """Execute generated code in a Daytona workspace sandbox."""
    print_status("Initializing Daytona sandbox", 'info')

    start_time = time.time()
    config = DaytonaConfig(
        api_key=str(daytona_api_key),
        server_url=str(daytona_server_url),
        target="local"
    )
    daytona = Daytona(config=config)
    init_time = time.time() - start_time
    print_timing("Daytona initialization", init_time)

    # Create workspace
    start_time = time.time()
    params = CreateWorkspaceParams(language="python")
    workspace = daytona.create(params=params)
    workspace_creation_time = time.time() - start_time
    print_timing("Workspace creation", workspace_creation_time)

    try:
        # Execute the code
        print_status("Executing code in sandbox", 'info')
        start_time = time.time()
        response = workspace.process.code_run(code)
        execution_time = time.time() - start_time
        print_timing("Code execution", execution_time)

        if response.code != 0:
            print_status(f"Execution failed: {response.code}", 'error')
            return f"Error: {response.code} {response.result}"
        return response.result
    finally:
        # Cleanup
        start_time = time.time()
        daytona.remove(workspace)
        cleanup_time = time.time() - start_time
        print_timing("Workspace cleanup", cleanup_time)

if __name__ == "__main__":
    total_start_time = time.time()

    # Generate Python code
    task = "What is the square root of the meaning of life and everything?"
    generated_code = generate_code("Python", task)

    # Display the generated code
    print_code(generated_code)

    # Execute in sandbox
    result = execute_in_sandbox(generated_code)
    print_status("Code execution result:", 'success')
    print(colored(result, 'green'))

    total_time = time.time() - total_start_time
    print_timing("Total execution", total_time)