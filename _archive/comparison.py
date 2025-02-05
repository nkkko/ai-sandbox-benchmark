from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
from e2b_code_interpreter import Sandbox
import os
from dotenv import load_dotenv
import time
from termcolor import colored
from datetime import datetime
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter
from tabulate import tabulate

# Load environment variables from .env file
load_dotenv()

class TimingMetrics:
    def __init__(self):
        self.metrics = {
            "Initialization": 0,
            "Workspace Creation": 0,
            "Code Execution": 0,
            "Cleanup": 0
        }

    def add_metric(self, name, time):
        if name in self.metrics:
            self.metrics[name] = time * 1000  # Convert to milliseconds

def print_timing(description: str, elapsed_time: float):
    """Print timing information in color."""
    elapsed_ms = elapsed_time * 1000
    print(colored(
        f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {description}: {elapsed_ms:.2f} ms",
        'cyan'
    ))

def print_status(message: str, status: str = 'info'):
    """Print status messages in different colors based on type."""
    colors = {'info': 'blue', 'success': 'green', 'error': 'red', 'warning': 'yellow'}
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

def execute_in_daytona(code: str, metrics: TimingMetrics):
    """Execute code in Daytona sandbox."""
    print_status("Testing Daytona sandbox", 'info')

    # Initialization (creating client only)
    start_time = time.time()
    config = DaytonaConfig(
        api_key=str(os.getenv("DAYTONA_API_KEY")),
        server_url=str(os.getenv("DAYTONA_SERVER_URL")),
        target="local"
    )
    daytona = Daytona(config=config)
    metrics.add_metric("Initialization", time.time() - start_time)

    # Workspace Creation
    start_time = time.time()
    params = CreateWorkspaceParams(language="python")
    workspace = daytona.create(params=params)
    metrics.add_metric("Workspace Creation", time.time() - start_time)

    try:
        # Code Execution
        start_time = time.time()
        response = workspace.process.code_run(code)
        metrics.add_metric("Code Execution", time.time() - start_time)
        return response.result
    finally:
        # Cleanup
        start_time = time.time()
        daytona.remove(workspace)
        metrics.add_metric("Cleanup", time.time() - start_time)

def execute_in_e2b(code: str, metrics: TimingMetrics):
    """Execute code in e2b sandbox."""
    print_status("Testing e2b sandbox", 'info')

    # Initialization (creating client only)
    start_time = time.time()
    metrics.add_metric("Initialization", time.time() - start_time)

    # Workspace Creation (creating sandbox)
    start_time = time.time()
    sandbox = Sandbox()
    metrics.add_metric("Workspace Creation", time.time() - start_time)

    try:
        # Code Execution
        start_time = time.time()
        execution = sandbox.run_code(code)
        metrics.add_metric("Code Execution", time.time() - start_time)
        return execution.logs
    finally:
        # Cleanup
        start_time = time.time()
        sandbox.kill()
        metrics.add_metric("Cleanup", time.time() - start_time)

def print_comparison_table(daytona_metrics: TimingMetrics, e2b_metrics: TimingMetrics):
    """Print a comparison table of the timing metrics."""
    headers = ["Operation", "Daytona (ms)", "e2b (ms)", "Difference (ms)"]
    table_data = []

    for operation in ["Initialization", "Workspace Creation", "Code Execution", "Cleanup"]:
        daytona_time = daytona_metrics.metrics[operation]
        e2b_time = e2b_metrics.metrics[operation]
        diff = abs(daytona_time - e2b_time)
        faster = "Daytona" if daytona_time < e2b_time else "e2b"

        table_data.append([
            operation,
            f"{daytona_time:.2f}" + (" ✓" if faster == "Daytona" else ""),
            f"{e2b_time:.2f}" + (" ✓" if faster == "e2b" else ""),
            f"{diff:.2f} ({faster} faster)"
        ])

    # Add total time row
    daytona_total = sum(daytona_metrics.metrics.values())
    e2b_total = sum(e2b_metrics.metrics.values())
    total_diff = abs(daytona_total - e2b_total)
    faster_total = "Daytona" if daytona_total < e2b_total else "e2b"

    table_data.append([
        "Total Time",
        f"{daytona_total:.2f}" + (" ✓" if faster_total == "Daytona" else ""),
        f"{e2b_total:.2f}" + (" ✓" if faster_total == "e2b" else ""),
        f"{total_diff:.2f} ({faster_total} faster)"
    ])

    print("\n" + colored("Performance Comparison:", 'yellow', attrs=['bold']))
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def generate_code(task: str):
    """Generate code using LangChain."""
    llm = OpenAI(temperature=0.2, max_tokens=1000)
    prompt = PromptTemplate(
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
    code_chain = prompt | llm
    return code_chain.invoke({"language": "Python", "task": task})

if __name__ == "__main__":
    # Environment checks
    required_vars = ["OPENAI_API_KEY", "DAYTONA_API_KEY", "DAYTONA_SERVER_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Generate test code
    task = "Write a program that calculates and prints:\n" \
           "1. The square root of 42\n" \
           "2. The first 5 Fibonacci numbers\n" \
           "3. The current date and time"

    generated_code = generate_code(task)
    print_code(generated_code)

    # Initialize metrics
    daytona_metrics = TimingMetrics()
    e2b_metrics = TimingMetrics()

    # Run Daytona test
    print_status("\nExecuting code in Daytona sandbox:", 'info')
    daytona_result = execute_in_daytona(generated_code, daytona_metrics)
    print_status("Daytona Result:", 'success')
    print(colored(daytona_result, 'green'))

    # Run e2b test
    print_status("\nExecuting code in e2b sandbox:", 'info')
    e2b_result = execute_in_e2b(generated_code, e2b_metrics)
    print_status("e2b Result:", 'success')
    if isinstance(e2b_result, str):
        print(colored(e2b_result, 'green'))
    else:
        print(colored("stdout:", 'blue'))
        for line in e2b_result.stdout:
            print(colored(line.strip(), 'green'))
        if e2b_result.stderr:
            print(colored("stderr:", 'red'))
            for line in e2b_result.stderr:
                print(colored(line.strip(), 'red'))

    # Print comparison
    print_comparison_table(daytona_metrics, e2b_metrics)