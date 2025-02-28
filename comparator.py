#!/usr/bin/env python3
import asyncio
import os
import time
import logging
import argparse
import importlib
import inspect
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from termcolor import colored
from tabulate import tabulate
import numpy as np
from typing import Dict, Any, Callable, List, Tuple
import requests

# Import EnhancedTimingMetrics from metrics instead of from comparator (avoids circular dependency)
from metrics import EnhancedTimingMetrics

# Dynamically import all modules in the tests directory
TESTS_DIR = 'tests'
defined_tests = {}
test_id = 1
for filename in os.listdir(TESTS_DIR):
    if filename.endswith('.py') and not filename.startswith('__'):
        module_name = filename[:-3]
        module = importlib.import_module(f'{TESTS_DIR}.{module_name}')
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if name.startswith('test_'):
                defined_tests[test_id] = func
                test_id += 1

# Import providers from separate modules
from providers import daytona, e2b, codesandbox, modal

# Map provider names to their corresponding execute() implementations.
# Note: the daytona.execute() requires (code, executor, target_region).
provider_executors = {
    'daytona': daytona.execute,
    'e2b': e2b.execute,
    'codesandbox': codesandbox.execute,
    'modal': modal.execute
}

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
            # Convert to milliseconds
            self.metrics[name].append(time_value * 1000)

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

    async def run_test_on_provider(self, test_code_func: Callable, provider: str, executor: ThreadPoolExecutor, target_region: str) -> Tuple[str, Dict[str, Any], Any]:
        results = {'metrics': EnhancedTimingMetrics(), 'output': None}
        try:
            code = test_code_func()
            logger.info(f"Executing test on {provider}...")
            if provider == "daytona":
                # Daytona requires additional parameters: executor and target_region.
                output, metrics = await provider_executors[provider](code, executor, target_region)
            else:
                output, metrics = await provider_executors[provider](code)
            # Merge metrics from executed provider into our results
            for metric_name, metric_values in metrics.metrics.items():
                if metric_values:
                    results['metrics'].metrics[metric_name].extend(metric_values)
            results['output'] = output
            logger.info(f"Completed {provider} execution")
            return provider, results, None
        except Exception as e:
            logger.error(f"Failed to execute {provider}: {str(e)}")
            results['metrics'].add_error(str(e))
            return provider, results, e

    async def run_comparison(self, tests: Dict[int, Callable], providers: List[str], measurement_runs: int, target_region: str) -> Dict[str, Any]:
        overall_results = {}
        logger.info("Starting comparison run...")

        # Handle tests that should only run once
        single_run_tests = {test_id: func for test_id, func in tests.items() 
                           if hasattr(func, 'single_run') and func.single_run}
        
        multi_run_tests = {test_id: func for test_id, func in tests.items()
                          if test_id not in single_run_tests}
        
        if single_run_tests:
            test_names = ", ".join([f"{test_id}:{func.__name__}" for test_id, func in single_run_tests.items()])
            logger.info(f"The following tests will only run once (ignoring measurement_runs): {test_names}")

        logger.info("Performing warmup runs...")
        for i in range(self.warmup_runs):
            logger.info(f"Warmup run {i+1}/{self.warmup_runs}")
            # Only do warmup runs for multi-run tests
            for test_id, test_code_func in multi_run_tests.items():
                for provider in providers:
                    async with asyncio.Semaphore(self.num_concurrent_providers):
                        with ThreadPoolExecutor(max_workers=self.num_concurrent_providers) as executor:
                            await self.run_test_on_provider(test_code_func, provider, executor, target_region)

        # Process single-run tests first (one run only)
        if single_run_tests:
            logger.info("Performing single-run tests...")
            for test_id, test_code_func in single_run_tests.items():
                logger.info(f"Running test {test_id}: {test_code_func.__name__} (single run)")
                test_results = overall_results.setdefault(f"test_{test_id}", {})
                run_results = test_results.setdefault("run_1", {})

                measurement_tasks = []
                with ThreadPoolExecutor(max_workers=self.num_concurrent_providers) as executor:
                    for provider in providers:
                        task = asyncio.create_task(self.run_test_on_provider(test_code_func, provider, executor, target_region))
                        measurement_tasks.append(task)

                    provider_run_results = await asyncio.gather(*measurement_tasks, return_exceptions=True)
                    for i, provider_result in enumerate(provider_run_results):
                        provider = providers[i]
                        if isinstance(provider_result, Exception):
                            logger.error(f"Test {test_id}: Failed to execute {provider}: {str(provider_result)}")
                            run_results[provider] = {'metrics': EnhancedTimingMetrics(), 'output': None, 'error': str(provider_result)}
                        else:
                            p_name, p_results, error = provider_result
                            run_results[p_name] = p_results
                            if error:
                                run_results[p_name]['error'] = str(error)

        # Process multi-run tests
        if multi_run_tests:
            logger.info(f"Performing {measurement_runs} measurement runs for standard tests...")
            for run in range(measurement_runs):
                logger.info(f"Measurement run {run+1}/{measurement_runs}")
                for test_id, test_code_func in multi_run_tests.items():
                    test_results = overall_results.setdefault(f"test_{test_id}", {})
                    run_results = test_results.setdefault(f"run_{run+1}", {})

                    measurement_tasks = []
                    with ThreadPoolExecutor(max_workers=self.num_concurrent_providers) as executor:
                        for provider in providers:
                            task = asyncio.create_task(self.run_test_on_provider(test_code_func, provider, executor, target_region))
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
    def print_summary_info(warmup_runs: int, measurement_runs: int, tests: dict, providers: list):
        print("\n" + "=" * 80)
        print("Test Configuration Summary".center(80))
        print("=" * 80)
        print(f"Warmup Runs: {warmup_runs}")
        print(f"Measurement Runs: {measurement_runs}")
        tests_used = ', '.join(f"{tid}:{func.__name__}" for tid, func in tests.items())
        print(f"Tests Used ({len(tests)}): {tests_used}")
        print(f"Providers Used: {', '.join(providers)}")
        print("=" * 80 + "\n")

    @staticmethod
    def print_detailed_comparison(
            overall_results: dict,
            tests: dict,
            measurement_runs: int,
            warmup_runs: int,
            providers: list
        ):
        # Print overall configuration details.
        ResultsVisualizer.print_summary_info(warmup_runs, measurement_runs, tests, providers)

        # Iterate over each test.
        for test_id, test_code_func in tests.items():
            print(f"\n{colored(f'Performance Comparison for Test {test_id}: {test_code_func.__name__}', 'yellow', attrs=['bold'])}")

            headers = ["Metric", "Daytona", "e2b", "CodeSandbox", "Modal"]
            table_data = []
            test_results = overall_results.get(f"test_{test_id}", {})

            # Optionally, print out an example output from the first available provider.
            first_run_results = test_results.get("run_1", {})
            first_provider_output = None
            for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                if provider in first_run_results and 'output' in first_run_results[provider]:
                    first_provider_output = first_run_results[provider]['output']
                    break
            if first_provider_output:
                print(f"\nExample Output (from first run, first available provider):\n{first_provider_output}")

            # Build the main metrics table.
            for metric in ["Workspace Creation", "Code Execution", "Cleanup"]:
                row = [metric]
                for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                    all_runs_metrics = []
                    for run_num in range(1, measurement_runs + 1):
                        run_results = test_results.get(f"run_{run_num}", {})
                        if provider in run_results:
                            run_metric = run_results[provider]['metrics'].get_statistics().get(metric, {})
                            if run_metric:
                                all_runs_metrics.append(run_metric['mean'])
                    if all_runs_metrics:
                        avg_metric = np.mean(all_runs_metrics)
                        std_metric = np.std(all_runs_metrics)
                        row.append(f"{avg_metric:.2f}ms (±{std_metric:.2f})")
                    else:
                        row.append("N/A")
                table_data.append(row)

            # Compute and display the total time row.
            row = ["Total Time"]
            platform_totals = {}
            for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                total_times = []
                for run_num in range(1, measurement_runs + 1):
                    run_results = test_results.get(f"run_{run_num}", {})
                    if provider in run_results:
                        total_times.append(run_results[provider]['metrics'].get_total_time())
                if total_times:
                    provider_total = np.mean(total_times)
                    platform_totals[provider] = provider_total
                    row.append(f"{provider_total:.2f}ms")
                else:
                    row.append("N/A")
            table_data.append(row)

            # Compute comparisons versus Daytona.
            daytona_total = platform_totals.get('daytona', 0)
            percentage_comparisons = []
            for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                if provider == "daytona" or daytona_total == 0:
                    percentage_comparisons.append("0%")
                elif provider in platform_totals:
                    diff_percentage = ((platform_totals[provider] - daytona_total) / daytona_total * 100)
                    percentage_comparisons.append(f"{diff_percentage:+.1f}%")
                else:
                    percentage_comparisons.append("N/A")
            table_data.append(["vs Daytona %"] + percentage_comparisons)

            # Print out the main metrics table.
            print(tabulate(table_data, headers=headers, tablefmt="grid"))

            # Build the failure summary table.
            fail_table = []
            fail_headers = ["Provider", "Failed Runs (out of {})".format(measurement_runs)]
            errors_found = False
            for provider in ["daytona", "e2b", "codesandbox", "modal"]:
                fail_count = 0
                for run_num in range(1, measurement_runs + 1):
                    run_results = test_results.get(f"run_{run_num}", {})
                    if provider in run_results and run_results[provider].get('error'):
                        fail_count += 1
                fail_table.append([provider.capitalize(), f"{fail_count}/{measurement_runs}"])
                if fail_count > 0:
                    errors_found = True

            if errors_found:
                print("\n" + colored(f"Failure Summary for Test {test_id}: {test_code_func.__name__}", 'red', attrs=['bold']))
                print(tabulate(fail_table, headers=fail_headers, tablefmt="grid"))
            else:
                print("\nNo failures recorded for this test.")


async def main(args):
    executor_obj = SandboxExecutor(warmup_runs=args.warmup_runs, measurement_runs=args.runs, num_concurrent_providers=4)

    tests_to_run = {}
    if args.tests == "all":
        tests_to_run = defined_tests
    else:
        for test_id in map(int, args.tests.split(',')):
            if test_id in defined_tests:
                tests_to_run[test_id] = defined_tests[test_id]
            else:
                logger.warning(f"Test ID {test_id} not found and will be skipped.")

    providers_to_run = args.providers.split(',')

    try:
        overall_results = await executor_obj.run_comparison(tests_to_run, providers_to_run, args.runs, args.target_region)
        visualizer = ResultsVisualizer()
        # Passing measurement_runs, warmup_runs and providers list
        visualizer.print_detailed_comparison(overall_results, tests_to_run, args.runs, args.warmup_runs, providers_to_run)
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run sandbox performance comparison tests.")
    parser.add_argument('--tests', '-t', type=str, default='all',
                        help='Comma-separated list of test IDs to run (or "all" for all tests). Default: all')
    parser.add_argument('--providers', '-p', type=str, default='daytona,e2b,codesandbox,modal',
                        help='Comma-separated list of providers to test. Default: daytona,e2b,codesandbox,modal')
    parser.add_argument('--runs', '-r', type=int, default=10,
                        help='Number of measurement runs per test/provider. Default: 10')
    parser.add_argument('--warmup-runs', '-w', type=int, default=1,
                        help='Number of warmup runs. Default: 1')
    parser.add_argument('--target-region', type=str, default='eu',
                        help='Target region (eu, us, asia). Default: eu')

    args = parser.parse_args()
    if args.tests != "all":
        try:
            test_ids = list(map(int, args.tests.split(',')))
        except ValueError:
            parser.error("--tests must be 'all' or comma-separated integers.")
    asyncio.run(main(args))
