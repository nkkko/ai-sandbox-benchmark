# 1. Make sure you have all the dependencies installed:
# pip install langchain-openai daytona-sdk e2b-code-interpreter modal-client python-dotenv termcolor tabulate scipy numpy requests argparse
# 2. Set up environment variables: Ensure you have OPENAI_API_KEY, DAYTONA_API_KEY, DAYTONA_SERVER_URL,
# and CSB_API_KEY set in your .env file or environment variables.
# 3. Run CodeSandbox server: node codesandbox-service.js
# 4. Run the Python script: python compare_4c.py -w 0 -t 1 -p daytona -r 5

import asyncio
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
from e2b_code_interpreter import Sandbox
import modal
import os
from dotenv import load_dotenv
import time
from termcolor import colored
from tabulate import tabulate
import numpy as np
import logging
from dataclasses import dataclass
from typing import Dict, Any, Callable, List, Tuple
import requests
from concurrent.futures import ThreadPoolExecutor
import argparse
import inspect
import importlib

# Dynamically import all modules in the tests directory
TESTS_DIR = 'tests'

defined_tests = {}
test_id = 1

for filename in os.listdir(TESTS_DIR):
    if filename.endswith('.py') and not filename.startswith('__'):
        module_name = filename[:-3]
        module = importlib.import_module(f'{TESTS_DIR}.{module_name}')

        # Iterate over all functions in the module
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith('test_'):
                defined_tests[test_id] = func
                test_id += 1


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedTimingMetrics:
    def __init__(self):
        self.metrics = {
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
    def __init__(self, warmup_runs: int = 1, measurement_runs: int = 10, num_concurrent_providers: int = 4):
        self.warmup_runs = warmup_runs
        self.measurement_runs = measurement_runs
        self.num_concurrent_providers = num_concurrent_providers
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
            logger.info(f"Found {description}")

    async def _execute_daytona_async(self, code: str, executor: ThreadPoolExecutor, target_region: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()
        workspace = None
        daytona = None
        loop = asyncio.get_running_loop()

        try:
            logger.info("Creating Daytona workspace...")
            start_time = time.time()
            config = DaytonaConfig(
                api_key=str(os.getenv("DAYTONA_API_KEY")),
                server_url=str(os.getenv("DAYTONA_SERVER_URL")),
                target=target_region # Use the configurable target_region
            )
            daytona = Daytona(config=config)
            params = CreateWorkspaceParams(language="python")
            workspace = await loop.run_in_executor(executor, daytona.create, params)
            logger.info(f"Workspace created: {workspace.id}")
            metrics.add_metric("Workspace Creation", time.time() - start_time)

            logger.info("Executing code in Daytona...")
            start_time = time.time()
            response = await loop.run_in_executor(executor, workspace.process.code_run, code)
            logger.info(f"Code execution completed in workspace {workspace.id}: {response}")
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
                    logger.info(f"Cleaning up Daytona workspace: {workspace.id}...")
                    await loop.run_in_executor(executor, daytona.remove, workspace)
                    logger.info(f"Daytona cleanup completed for workspace {workspace.id}")
                    metrics.add_metric("Cleanup", time.time() - start_time)
                except Exception as e:
                    logger.error(f"Daytona cleanup error for workspace {workspace.id}: {str(e)}")
                    metrics.add_error(f"Cleanup error: {str(e)}")


    async def _execute_e2b_async(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()
        sandbox = None

        try:
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

    async def _execute_codesandbox_async(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()

        try:
            logger.info("Sending request to CodeSandbox...")
            start_time = time.time()
            response = requests.post(
                'http://localhost:3000/execute',
                json={'code': code},
                timeout=30
            )
            logger.info(f"CodeSandbox response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.info(f"CodeSandbox execution completed")

            # Add metrics from the service
            for metric_name, value in result['metrics'].items():
                metrics.add_metric(
                    {
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

    async def _execute_modal_async(self, code: str) -> tuple[Any, EnhancedTimingMetrics]:
        metrics = EnhancedTimingMetrics()
        sandbox = None
        app = None

        try:
            logger.info("Creating Modal sandbox...")
            start_time = time.time()
            app = modal.App.lookup("code-comparison", create_if_missing=True)
            sandbox = modal.Sandbox.create(
                image=modal.Image.debian_slim().pip_install("numpy", "pandas"),
                app=app
            )
            metrics.add_metric("Workspace Creation", time.time() - start_time)

            logger.info("Executing code in Modal...")
            start_time = time.time()
            # Write code to a temporary file
            with open("/tmp/modal_code.py", "w") as f:
                f.write(code)

            # Execute the code
            process = sandbox.exec("python", "/tmp/modal_code.py")
            output = process.stdout.read()
            metrics.add_metric("Code Execution", time.time() - start_time)

            return output, metrics

        except Exception as e:
            metrics.add_error(f"Modal error: {str(e)}")
            logger.error(f"Modal execution error: {str(e)}")
            raise
        finally:
            if sandbox:
                start_time = time.time()
                try:
                    logger.info("Cleaning up Modal sandbox...")
                    sandbox.terminate()
                    logger.info("Modal cleanup completed")
                    metrics.add_metric("Cleanup", time.time() - start_time)
                except Exception as e:
                    logger.error(f"Modal cleanup error: {str(e)}")
                    metrics.add_error(f"Cleanup error: {str(e)}")


    async def run_test_on_provider(self, test_code_func: Callable, provider: str, executor: ThreadPoolExecutor, target_region: str) -> Tuple[str, Dict[str, Any], Any]:
        """Runs a specific test function on a given provider."""
        results = {'metrics': EnhancedTimingMetrics(), 'output': None}
        executors = {
            'daytona': self._execute_daytona_async,
            'e2b': self._execute_e2b_async,
            'codesandbox': self._execute_codesandbox_async,
            'modal': self._execute_modal_async
        }
        executor_func = executors[provider]
        code = test_code_func()

        try:
            logger.info(f"Executing test on {provider}...")
            if provider == 'daytona':
                output, metrics = await executor_func(code, executor, target_region) # Pass target_region
            else:
                output, metrics = await executor_func(code)
            for metric_name, metric_values in metrics.metrics.items():
                if metric_values:
                    results['metrics'].metrics[metric_name].extend(metric_values)
            results['output'] = output
            logger.info(f"Completed {provider} execution")
            return provider, results, None  # No error

        except Exception as e:
            logger.error(f"Failed to execute {provider}: {str(e)}")
            results['metrics'].add_error(str(e))
            return provider, results, e  # Return error

    async def run_comparison(self, tests: Dict[int, Callable], providers: List[str], measurement_runs: int, target_region: str) -> Dict[str, Any]:
        overall_results = {}

        logger.info("Starting comparison run...")

        logger.info("Performing warmup runs...")
        for i in range(self.warmup_runs):
            logger.info(f"Warmup run {i+1}/{self.warmup_runs}")
            for test_id, test_code_func in tests.items():
                for provider in providers:
                    async with asyncio.Semaphore(self.num_concurrent_providers): # Limit concurrent providers during warmup if needed
                        with ThreadPoolExecutor(max_workers=self.num_concurrent_providers) as executor: # Use thread pool for daytona create/remove
                            await self.run_test_on_provider(test_code_func, provider, executor, target_region) # Pass target_region

        logger.info(f"Performing {measurement_runs} measurement runs...")
        for run in range(measurement_runs):
            logger.info(f"Measurement run {run+1}/{measurement_runs}")
            for test_id, test_code_func in tests.items():
                test_results = overall_results.setdefault(f"test_{test_id}", {})
                run_results = test_results.setdefault(f"run_{run+1}", {})

                measurement_tasks = []
                with ThreadPoolExecutor(max_workers=self.num_concurrent_providers) as executor: # Use thread pool for daytona create/remove
                    for provider in providers:
                        task = asyncio.create_task(self.run_test_on_provider(test_code_func, provider, executor, target_region)) # Pass target_region
                        measurement_tasks.append(task)

                    provider_run_results = await asyncio.gather(*measurement_tasks, return_exceptions=True)

                    for i, provider_result in enumerate(provider_run_results):
                        provider = providers[i]
                        if isinstance(provider_result, Exception):
                            logger.error(f"Run {run+1}, Test {test_id}: Failed to execute {provider}: {str(provider_result)}")
                            run_results[provider] = {'metrics': EnhancedTimingMetrics(), 'output': None, 'error': str(provider_result)}
                        else:
                            p_name, p_results, error = provider_result
                            run_results[p_name] = p_results
                            if error:
                                run_results[p_name]['error'] = str(error)


        return overall_results

class ResultsVisualizer:
    @staticmethod
    def print_detailed_comparison(overall_results: Dict[str, Any], tests: Dict[int, Callable], measurement_runs: int): # Add measurement_runs
        for test_id, test_code_func in tests.items():
            print(f"\n{colored(f'Performance Comparison for Test {test_id}: {test_code_func.__name__}', 'yellow', attrs=['bold'])}")
            headers = ["Metric", "Daytona", "e2b", "CodeSandbox", "Modal"]
            table_data = []
            test_results = overall_results.get(f"test_{test_id}", {})
            first_run_results = test_results.get("run_1", {}) # Use results from the first run for output example

            # Output example from the first run (if available)
            first_provider_output = None
            for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                if provider in first_run_results and 'output' in first_run_results[provider]:
                    first_provider_output = first_run_results[provider]['output']
                    break # Just take the first available output
            if first_provider_output:
                print(f"\nExample Output (from first run, first available provider):\n{first_provider_output}")

            for metric in ["Workspace Creation", "Code Execution", "Cleanup"]:
                row = [metric]
                for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                    all_runs_metrics = []
                    for run_num in range(1, measurement_runs + 1): # Use passed measurement_runs
                        run_results = test_results.get(f"run_{run_num}", {})
                        if provider in run_results:
                            run_metric = run_results[provider]['metrics'].get_statistics().get(metric, {})
                            if run_metric:
                                all_runs_metrics.append(run_metric['mean'])

                    if all_runs_metrics:
                        avg_metric_mean = np.mean(all_runs_metrics)
                        std_metric_mean = np.std(all_runs_metrics)
                        row.append(f"{avg_metric_mean:.2f}ms (±{std_metric_mean:.2f})")
                    else:
                        row.append("N/A")
                table_data.append(row)

            # Add total times
            row = ["Total Time"]
            platform_totals = {}
            for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                total_times_for_provider = []
                for run_num in range(1, measurement_runs + 1): # Use passed measurement_runs
                    run_results = test_results.get(f"run_{run_num}", {})
                    if provider in run_results:
                        total_times_for_provider.append(run_results[provider]['metrics'].get_total_time())
                if total_times_for_provider:
                    platform_total = np.mean(total_times_for_provider)
                    platform_totals[provider] = platform_total
                    row.append(f"{platform_total:.2f}ms")
                else:
                    row.append("N/A")
            table_data.append(row)

            # Add percentage comparison vs Daytona
            daytona_total = platform_totals.get('daytona', 0) # Default to 0 if no daytona results
            percentage_comparisons = []
            for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                if provider == "daytona" or daytona_total == 0: # Avoid division by zero, or if daytona has no results
                    percentage_comparisons.append("0%")  # Reference point
                elif provider in platform_totals:
                    diff_percentage = ((platform_totals[provider] - daytona_total) / daytona_total * 100)
                    percentage_comparisons.append(f"{diff_percentage:+.1f}%")  # + sign for positive values
                else:
                    percentage_comparisons.append("N/A")


            table_data.append([
                "vs Daytona %",
                *percentage_comparisons
            ])

            print(tabulate(table_data, headers=headers, tablefmt="grid"))

            # Print errors if any
            for provider in ['daytona', 'e2b', 'codesandbox', 'modal']:
                all_errors = []
                for run_num in range(1, measurement_runs + 1): # Use passed measurement_runs
                    run_results = test_results.get(f"run_{run_num}", {})
                    if provider in run_results and 'error' in run_results[provider] and run_results[provider]['error']:
                        all_errors.append(run_results[provider]['error'])
                if all_errors:
                    print(f"\n{provider.capitalize()} Errors for Test {test_id}:")
                    for error in all_errors:
                        print(colored(f"- {error}", 'red'))


async def main(args):
    executor = SandboxExecutor(warmup_runs=args.warmup_runs, measurement_runs=args.runs, num_concurrent_providers=4)

    tests_to_run = {}
    if args.tests == "all":
        tests_to_run = defined_tests
    else:
        for test_id in map(int, args.tests.split(',')): # Parse comma separated string to integers
            if test_id in defined_tests:
                tests_to_run[test_id] = defined_tests[test_id]
            else:
                logger.warning(f"Test ID {test_id} not found and will be skipped.")

    providers_to_run = args.providers.split(',') # Comma separated string to list

    try:
        overall_results = await executor.run_comparison(tests_to_run, providers_to_run, args.runs, args.target_region) # Pass target_region

        visualizer = ResultsVisualizer()
        visualizer.print_detailed_comparison(overall_results, tests_to_run, args.runs) # Pass measurement_runs

    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run sandbox performance comparison tests.")
    parser.add_argument('--tests', '-t', type=str, default='all', help='Comma-separated list of test IDs to run (or "all" for all tests). Default: all')
    parser.add_argument('--providers', '-p', type=str, default='daytona,e2b,codesandbox,modal', help='Comma-separated list of providers to test. Default: daytona,e2b,codesandbox,modal')
    parser.add_argument('--runs', '-r', type=int, default=10, help='Number of measurement runs per test/provider. Default: 10')
    parser.add_argument('--warmup-runs', '-w', type=int, default=1, help='Number of warmup runs. Default: 1')
    parser.add_argument('--target-region', type=str, default='eu', help='Daytona target region (eu, us, asia). Default: eu') # Add target_region argument


    args = parser.parse_args()

    if args.tests != "all":
        try:
            test_ids = list(map(int, args.tests.split(',')))
        except ValueError:
            parser.error("--tests must be 'all' or comma-separated integers.")

    asyncio.run(main(args))