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
        """Add a timing measurement to the specified metric category."""
        if name in self.metrics:
            self.metrics[name].append(time_value * 1000)  # Convert to milliseconds

    def add_error(self, error: str):
        """Record an error that occurred during execution."""
        self.errors.append(error)

    def get_statistics(self) -> Dict[str, Dict[str, float]]:
        """Calculate statistics for each metric category."""
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
        """Calculate total execution time across all metrics."""
        return sum(np.mean(times) for times in self.metrics.values() if times)

class SandboxExecutor:
    def __init__(self, warmup_runs: int = 1, measurement_runs: int = 10):
        self.warmup_runs = warmup_runs
        self.measurement_runs = measurement_runs
        load_dotenv()
        self._validate_environment()

    def _validate_environment(self):
        """Validate that all required environment variables are present."""
        required_vars = ["OPENAI_API_KEY", "DAYTONA_API_KEY", "DAYTONA_SERVER_URL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def execute_daytona(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        """Execute code in Daytona sandbox with timing metrics."""
        metrics = EnhancedTimingMetrics()
        workspace = None

        try:
            # Initialization
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

            # Code Execution
            start_time = time.time()
            response = workspace.process.code_run(code)
            metrics.add_metric("Code Execution", time.time() - start_time)

            return response.result, metrics

        except Exception as e:
            metrics.add_error(str(e))
            logger.error(f"Daytona execution error: {str(e)}")
            raise
        finally:
            # Cleanup
            if workspace:
                start_time = time.time()
                try:
                    daytona.remove(workspace)
                except Exception as e:
                    logger.error(f"Daytona cleanup error: {str(e)}")
                metrics.add_metric("Cleanup", time.time() - start_time)

    def execute_e2b(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        """Execute code in e2b sandbox with timing metrics."""
        metrics = EnhancedTimingMetrics()
        sandbox = None

        try:
            # Initialization
            start_time = time.time()
            metrics.add_metric("Initialization", time.time() - start_time)

            # Workspace Creation
            start_time = time.time()
            sandbox = Sandbox()
            metrics.add_metric("Workspace Creation", time.time() - start_time)

            # Code Execution
            start_time = time.time()
            execution = sandbox.run_code(code)
            metrics.add_metric("Code Execution", time.time() - start_time)

            return execution.logs, metrics

        except Exception as e:
            metrics.add_error(str(e))
            logger.error(f"e2b execution error: {str(e)}")
            raise
        finally:
            # Cleanup
            if sandbox:
                start_time = time.time()
                try:
                    sandbox.kill()
                except Exception as e:
                    logger.error(f"e2b cleanup error: {str(e)}")
                metrics.add_metric("Cleanup", time.time() - start_time)

    def run_comparison(self, code: str) -> Dict[str, Any]:
        """Run a full comparison between Daytona and e2b with warmup and multiple measurements."""
        results = {
            'daytona': {'metrics': EnhancedTimingMetrics(), 'output': None},
            'e2b': {'metrics': EnhancedTimingMetrics(), 'output': None}
        }

        # Warmup runs
        logger.info("Performing warmup runs...")
        for _ in range(self.warmup_runs):
            self.execute_daytona(code)
            self.execute_e2b(code)

        # Measurement runs
        logger.info(f"Performing {self.measurement_runs} measurement runs...")
        for run in range(self.measurement_runs):
            # Execute Daytona
            daytona_output, daytona_metrics = self.execute_daytona(code)
            # Accumulate metrics instead of overwriting
            for metric_name, metric_values in daytona_metrics.metrics.items():
                if metric_values:  # Only add if there's a value
                    results['daytona']['metrics'].metrics[metric_name].extend(metric_values)

            # Execute e2b
            e2b_output, e2b_metrics = self.execute_e2b(code)
            # Accumulate metrics instead of overwriting
            for metric_name, metric_values in e2b_metrics.metrics.items():
                if metric_values:  # Only add if there's a value
                    results['e2b']['metrics'].metrics[metric_name].extend(metric_values)

            # Store the last output (or you could store all outputs if needed)
            results['daytona']['output'] = daytona_output
            results['e2b']['output'] = e2b_output

        return results

class ResultsVisualizer:
    @staticmethod
    def print_detailed_comparison(results: Dict[str, Any]):
        """Print a detailed comparison of the results."""
        headers = ["Metric", "Daytona", "e2b", "Difference"]
        table_data = []

        # Calculate metrics for each category
        for metric in ["Initialization", "Workspace Creation", "Code Execution", "Cleanup"]:
            daytona_stats = results['daytona']['metrics'].get_statistics()[metric]
            e2b_stats = results['e2b']['metrics'].get_statistics()[metric]

            diff = abs(daytona_stats['mean'] - e2b_stats['mean'])
            faster = "Daytona" if daytona_stats['mean'] < e2b_stats['mean'] else "e2b"

            table_data.append([
                metric,
                f"{daytona_stats['mean']:.2f}ms (±{daytona_stats['std']:.2f})",
                f"{e2b_stats['mean']:.2f}ms (±{e2b_stats['std']:.2f})",
                f"{diff:.2f}ms ({faster} faster)"
            ])

        # Add total time comparison
        daytona_total = results['daytona']['metrics'].get_total_time()
        e2b_total = results['e2b']['metrics'].get_total_time()
        total_diff = abs(daytona_total - e2b_total)
        faster_total = "Daytona" if daytona_total < e2b_total else "e2b"

        table_data.append([
            "Total Time",
            f"{daytona_total:.2f}ms",
            f"{e2b_total:.2f}ms",
            f"{total_diff:.2f}ms ({faster_total} faster)"
        ])

        # Add percentage comparison
        slower_time = max(daytona_total, e2b_total)
        faster_time = min(daytona_total, e2b_total)
        percentage_diff = ((slower_time - faster_time) / faster_time) * 100

        table_data.append([
            "Percentage Difference",
            "",
            "",
            f"{percentage_diff:.1f}% ({faster_total} is faster)"
        ])

        print("\n" + colored("Detailed Performance Comparison:", 'yellow', attrs=['bold']))
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        # Print errors if any
        for platform in ['daytona', 'e2b']:
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