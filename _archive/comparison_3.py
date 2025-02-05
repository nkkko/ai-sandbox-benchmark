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
import numpy as np
from scipy import stats
import logging
from dataclasses import dataclass
from typing import Dict, Any
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedTimingMetrics:
    def __init__(self):
        self.metrics = {
            "Initialization": [],
            "Workspace Creation": [],
            "Code Execution": [],
            "Cleanup": []
        }
        self.errors = []

    def add_metric(self, name: str, time_value: float):
        if name in self.metrics:
            self.metrics[name].append(time_value * 1000)  # Convert to milliseconds

    def add_error(self, error: str):
        self.errors.append(error)

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        stats_dict = {}
        for name, measurements in self.metrics.items():
            if measurements:
                stats_dict[name] = {
                    'mean': np.mean(measurements),
                    'std': np.std(measurements),
                    'min': np.min(measurements),
                    'max': np.max(measurements)
                }
        return stats_dict

    def get_total_time(self) -> float:
        return sum(np.mean(times) for times in self.metrics.values() if times)

class SandboxExecutor:
    def __init__(self, warmup_runs: int = 1, measurement_runs: int = 10):
        self.warmup_runs = warmup_runs
        self.measurement_runs = measurement_runs
        load_dotenv()
        self._validate_environment()

    def _validate_environment(self):
        required_vars = {
            "OPENAI_API_KEY": "OpenAI API key",
            "DAYTONA_API_KEY": "Daytona API key",
            "DAYTONA_SERVER_URL": "Daytona server URL",
            "CSB_API_KEY": "CodeSandbox API key"
        }

        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value:
                raise ValueError(f"Missing {description} in environment variables: {var}")
            logger.info(f"Found {description}")  # Add logging but mask sensitive values

    def execute_daytona(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()
        workspace = None
        daytona = None

        try:
            logger.info("Initializing Daytona...")
            start_time = time.time()
            config = DaytonaConfig(
                api_key=str(os.getenv("DAYTONA_API_KEY")),
                server_url=str(os.getenv("DAYTONA_SERVER_URL")),
                target="local"
            )
            daytona = Daytona(config=config)
            metrics.add_metric("Initialization", time.time() - start_time)

            logger.info("Creating Daytona workspace...")
            start_time = time.time()
            params = CreateWorkspaceParams(language="python")
            workspace = daytona.create(params=params)
            logger.info(f"Workspace created: {workspace}")
            metrics.add_metric("Workspace Creation", time.time() - start_time)

            logger.info("Executing code in Daytona...")
            start_time = time.time()
            response = workspace.process.code_run(code)
            logger.info(f"Code execution completed: {response}")
            metrics.add_metric("Code Execution", time.time() - start_time)

            return response.result, metrics

        except Exception as e:
            metrics.add_error(str(e))
            logger.error(f"Daytona execution error: {str(e)}")
            raise
        finally:
            if workspace and daytona:
                start_time = time.time()
                try:
                    logger.info("Cleaning up Daytona workspace...")
                    daytona.remove(workspace)
                    logger.info("Daytona cleanup completed")
                    metrics.add_metric("Cleanup", time.time() - start_time)
                except Exception as e:
                    logger.error(f"Daytona cleanup error: {str(e)}")
                    metrics.add_error(f"Cleanup error: {str(e)}")

    def execute_e2b(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()
        sandbox = None

        try:
            start_time = time.time()
            metrics.add_metric("Initialization", time.time() - start_time)

            start_time = time.time()
            sandbox = Sandbox()
            metrics.add_metric("Workspace Creation", time.time() - start_time)

            start_time = time.time()
            execution = sandbox.run_code(code)
            metrics.add_metric("Code Execution", time.time() - start_time)

            return execution.logs, metrics

        except Exception as e:
            metrics.add_error(str(e))
            logger.error(f"e2b execution error: {str(e)}")
            raise
        finally:
            if sandbox:
                start_time = time.time()
                try:
                    sandbox.kill()
                except Exception as e:
                    logger.error(f"e2b cleanup error: {str(e)}")
                metrics.add_metric("Cleanup", time.time() - start_time)

    def execute_codesandbox(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()

        try:
            logger.info("Initializing CodeSandbox request...")  # Add logging
            start_time = time.time()
            metrics.add_metric("Initialization", time.time() - start_time)

            logger.info("Sending request to CodeSandbox...")  # Add logging
            response = requests.post(
                'http://localhost:3000/execute',
                json={'code': code},
                timeout=30
            )
            logger.info(f"CodeSandbox response status: {response.status_code}")  # Add logging
            response.raise_for_status()
            result = response.json()
            logger.info(f"CodeSandbox execution completed")  # Add logging

            # Add metrics from the service
            for metric_name, value in result['metrics'].items():
                metrics.add_metric(
                    {
                        'initialization': 'Initialization',
                        'workspaceCreation': 'Workspace Creation',
                        'codeExecution': 'Code Execution',
                        'cleanup': 'Cleanup'
                    }[metric_name],
                    value / 1000
                )

            return result['output'], metrics

        except requests.exceptions.ConnectionError:
            error_msg = "Failed to connect to CodeSandbox server. Is it running?"
            logger.error(error_msg)
            metrics.add_error(error_msg)
            raise
        except Exception as e:
            metrics.add_error(str(e))
            logger.error(f"CodeSandbox execution error: {str(e)}")
            raise

    def run_comparison(self, code: str) -> Dict[str, Any]:
        results = {
            'daytona': {'metrics': EnhancedTimingMetrics(), 'output': None},
            'e2b': {'metrics': EnhancedTimingMetrics(), 'output': None},
            'codesandbox': {'metrics': EnhancedTimingMetrics(), 'output': None}
        }

        logger.info("Starting comparison run...")  # Add logging

        logger.info("Performing warmup runs...")
        for i in range(self.warmup_runs):
            logger.info(f"Warmup run {i+1}/{self.warmup_runs}")  # Add logging
            for platform in ['daytona', 'e2b', 'codesandbox']:
                try:
                    logger.info(f"Warming up {platform}...")  # Add logging
                    executor = getattr(self, f"execute_{platform}")
                    executor(code)
                except Exception as e:
                    logger.error(f"Warmup failed for {platform}: {str(e)}")

        logger.info(f"Performing {self.measurement_runs} measurement runs...")
        for run in range(self.measurement_runs):
            logger.info(f"Measurement run {run+1}/{self.measurement_runs}")  # Add logging
            for platform, executor in {
                'daytona': self.execute_daytona,
                'e2b': self.execute_e2b,
                'codesandbox': self.execute_codesandbox
            }.items():
                try:
                    logger.info(f"Executing {platform}...")  # Add logging
                    output, metrics = executor(code)
                    for metric_name, metric_values in metrics.metrics.items():
                        if metric_values:
                            results[platform]['metrics'].metrics[metric_name].extend(metric_values)
                    results[platform]['output'] = output
                    logger.info(f"Completed {platform} execution")  # Add logging
                except Exception as e:
                    logger.error(f"Failed to execute {platform}: {str(e)}")
                    results[platform]['metrics'].add_error(str(e))

        return results

class ResultsVisualizer:
    @staticmethod
    def print_detailed_comparison(results: Dict[str, Any]):
        headers = ["Metric", "Daytona", "e2b", "CodeSandbox"]
        table_data = []

        for metric in ["Initialization", "Workspace Creation", "Code Execution", "Cleanup"]:
            row = [metric]
            for platform in ["daytona", "e2b", "codesandbox"]:
                stats = results[platform]['metrics'].get_statistics().get(metric, {})
                if stats:
                    row.append(f"{stats['mean']:.2f}ms (±{stats['std']:.2f})")
                else:
                    row.append("N/A")
            table_data.append(row)

        # Add total times
        row = ["Total Time"]
        platform_totals = {}
        for platform in ["daytona", "e2b", "codesandbox"]:
            total = results[platform]['metrics'].get_total_time()
            platform_totals[platform] = total
            row.append(f"{total:.2f}ms")
        table_data.append(row)

        # Find fastest platform
        fastest_platform = min(platform_totals.items(), key=lambda x: x[1])[0]
        slowest_platform = max(platform_totals.items(), key=lambda x: x[1])[0]
        percentage_diff = ((platform_totals[slowest_platform] - platform_totals[fastest_platform])
                         / platform_totals[fastest_platform] * 100)

        table_data.append([
            "Percentage Difference",
            "",
            "",
            f"{percentage_diff:.1f}% ({fastest_platform} is fastest)"
        ])

        print("\n" + colored("Detailed Performance Comparison:", 'yellow', attrs=['bold']))
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Print errors if any
        for platform in ['daytona', 'e2b', 'codesandbox']:
            errors = results[platform]['metrics'].errors
            if errors:
                print(f"\n{platform.capitalize()} Errors:")
                for error in errors:
                    print(colored(f"- {error}", 'red'))

def main():
    task = """Write a program that:
    1. Calculates the first 10 prime numbers
    2. Computes their sum and average
    3. Prints the results with appropriate formatting
    """

    executor = SandboxExecutor(warmup_runs=0, measurement_runs=2)

    try:
        llm = OpenAI(temperature=0.2, max_tokens=1000)
        prompt = PromptTemplate(
            input_variables=["task"],
            template="Write Python code for the following task:\n\n{task}\n\nCode:"
        )
        generated_code = llm(prompt.format(task=task))

        results = executor.run_comparison(generated_code)

        visualizer = ResultsVisualizer()
        visualizer.print_detailed_comparison(results)

    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()