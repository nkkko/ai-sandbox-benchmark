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
        required_vars = ["OPENAI_API_KEY", "DAYTONA_API_KEY", "DAYTONA_SERVER_URL", "CSB_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def execute_daytona(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()
        workspace = None

        try:
            start_time = time.time()
            config = DaytonaConfig(
                api_key=str(os.getenv("DAYTONA_API_KEY")),
                server_url=str(os.getenv("DAYTONA_SERVER_URL")),
                target="local"
            )
            daytona = Daytona(config=config)
            metrics.add_metric("Initialization", time.time() - start_time)

            start_time = time.time()
            params = CreateWorkspaceParams(language="python")
            workspace = daytona.create(params=params)
            metrics.add_metric("Workspace Creation", time.time() - start_time)

            start_time = time.time()
            response = workspace.process.code_run(code)
            metrics.add_metric("Code Execution", time.time() - start_time)

            return response.result, metrics

        except Exception as e:
            metrics.add_error(str(e))
            logger.error(f"Daytona execution error: {str(e)}")
            raise
        finally:
            if workspace:
                start_time = time.time()
                try:
                    daytona.remove(workspace)
                except Exception as e:
                    logger.error(f"Daytona cleanup error: {str(e)}")
                metrics.add_metric("Cleanup", time.time() - start_time)

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
            start_time = time.time()
            metrics.add_metric("Initialization", time.time() - start_time)

            response = requests.post(
                'http://localhost:3000/execute',
                json={'code': code},
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Add metrics from the service
            for metric_name, value in result['metrics'].items():
                metrics.add_metric(
                    {
                        'initialization': 'Initialization',
                        'workspaceCreation': 'Workspace Creation',
                        'codeExecution': 'Code Execution',
                        'cleanup': 'Cleanup'
                    }[metric_name],
                    value / 1000  # Convert from milliseconds
                )

            return result['output'], metrics

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

        logger.info("Performing warmup runs...")
        for _ in range(self.warmup_runs):
            self.execute_daytona(code)
            self.execute_e2b(code)
            self.execute_codesandbox(code)

        logger.info(f"Performing {self.measurement_runs} measurement runs...")
        for run in range(self.measurement_runs):
            # Execute all platforms
            for platform, executor in {
                'daytona': self.execute_daytona,
                'e2b': self.execute_e2b,
                'codesandbox': self.execute_codesandbox
            }.items():
                output, metrics = executor(code)
                for metric_name, metric_values in metrics.metrics.items():
                    if metric_values:
                        results[platform]['metrics'].metrics[metric_name].extend(metric_values)
                results[platform]['output'] = output

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

    executor = SandboxExecutor(warmup_runs=2, measurement_runs=5)

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