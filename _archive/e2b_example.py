from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from e2b_code_interpreter import Sandbox
import os
from dotenv import load_dotenv
import time
from termcolor import colored
from datetime import datetime
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter

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
    highlighted_code = highlight(code, PythonLexer(), Terminal256Formatter())
    print(highlighted_code.rstrip())
    print(colored("-" * 80, 'yellow') + "\n")

# Environment variable checks
start_time = time.time()
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment variables")

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
    """Execute generated code in an e2b sandbox."""
    print_status("Initializing e2b sandbox", 'info')

    start_time = time.time()
    sandbox = Sandbox()
    init_time = time.time() - start_time
    print_timing("Sandbox initialization", init_time)

    try:
        # Execute the code
        print_status("Executing code in sandbox", 'info')
        start_time = time.time()
        execution = sandbox.run_code(code)
        execution_time = time.time() - start_time
        print_timing("Code execution", execution_time)

        # List files in sandbox (optional, for debugging)
        #files_start_time = time.time()
        #files = sandbox.files.list("/")
        #files_time = time.time() - files_start_time
        #print_timing("Files listing", files_time)
        #print_status("Files in sandbox:", 'info')
        #print(colored(str(files), 'white'))

        return execution.logs

    except Exception as e:
        print_status(f"Execution failed: {str(e)}", 'error')
        return f"Error: {str(e)}"
    finally:
        # Cleanup
        start_time = time.time()
        sandbox.kill()
        cleanup_time = time.time() - start_time
        print_timing("Sandbox cleanup", cleanup_time)

if __name__ == "__main__":
    total_start_time = time.time()

    # Generate Python code
    task = "Calculate the meaning of life."
    generated_code = generate_code("Python", task)

    # Display the generated code
    print_code(generated_code)

    # Execute in sandbox
    result = execute_in_sandbox(generated_code)
    print_status("Code execution result:", 'success')
    print(colored(result, 'green'))

    total_time = time.time() - total_start_time
    print_timing("Total execution", total_time)