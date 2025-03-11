#!/usr/bin/env python3
"""
Script to help migrate tests to the new optimized test framework.

This script analyzes existing test files and generates migrated versions
with the new framework structure.
"""
import os
import re
import argparse
import ast
from typing import Dict, Any, List, Optional, Tuple

# Patterns to identify common code blocks
TIMER_PATTERN = re.compile(r'def\s+benchmark_timer.*?return\s+wrapper', re.DOTALL)
PACKAGE_INSTALL_PATTERN = re.compile(r'(import\s+subprocess.*?pip\s+install.*?)', re.DOTALL)
RESULTS_PATTERN = re.compile(r'print\(\s*["\']\\n\\n---\s*BENCHMARK\s*TIMING\s*DATA.*?END\s*BENCHMARK\s*TIMING\s*DATA\s*---["\'].*?\)', re.DOTALL)

# Template for migrated test
MIGRATED_TEST_TEMPLATE = '''"""
{docstring}
"""
from tests.test_utils import create_test_config
from tests.test_sandbox_utils import get_sandbox_utils

def {test_name}():
    """
    {test_description}
    """
    # Define test configuration
    config = create_test_config(
        env_vars={env_vars},
        single_run={single_run},
        packages={packages},
        is_info_test={is_info_test}
    )

    # Get the sandbox utilities code
    utils_code = get_sandbox_utils(
        include_timer={include_timer},
        include_results={include_results},
        include_packages={include_packages}
    )

    # Define the test-specific code
    test_code = """{test_code}"""

    # Combine the utilities and test code
    full_code = f"{{utils_code}}\\n\\n{{test_code}}"

    # Return the test configuration and code
    return {{
        "config": config,
        "code": full_code
    }}
'''

def extract_config(code: str) -> Dict[str, Any]:
    """Extract configuration from existing test code."""
    config = {
        "env_vars": [],
        "single_run": False,
        "packages": [],
        "is_info_test": False
    }

    # Try to parse the code to extract configuration
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                # Look for config dictionary
                for i, key in enumerate(node.keys):
                    if isinstance(key, ast.Str) and key.s == "config":
                        config_node = node.values[i]
                        if isinstance(config_node, ast.Dict):
                            for j, config_key in enumerate(config_node.keys):
                                if isinstance(config_key, ast.Str):
                                    if config_key.s == "env_vars" and isinstance(config_node.values[j], ast.List):
                                        config["env_vars"] = []  # Extract env vars if needed
                                    elif config_key.s == "single_run" and isinstance(config_node.values[j], ast.NameConstant):
                                        config["single_run"] = config_node.values[j].value
                                    elif config_key.s == "packages" and isinstance(config_node.values[j], ast.List):
                                        packages = []
                                        for elt in config_node.values[j].elts:
                                            if isinstance(elt, ast.Str):
                                                packages.append(elt.s)
                                        config["packages"] = packages
    except Exception as e:
        print(f"Error parsing code: {e}")

    # Check for is_info_test attribute
    if ".is_info_test = True" in code:
        config["is_info_test"] = True

    return config

def extract_test_code(code: str) -> str:
    """Extract test-specific code from existing test code."""
    # Remove the benchmark timer implementation
    code = TIMER_PATTERN.sub('', code)

    # Remove package installation boilerplate
    code = PACKAGE_INSTALL_PATTERN.sub('ensure_packages(["numpy", "scipy"])', code)

    # Replace results printing with print_benchmark_results
    code = RESULTS_PATTERN.sub('print_benchmark_results(test_result)', code)

    return code.strip()

def migrate_test(file_path: str, output_dir: Optional[str] = None) -> Tuple[bool, str]:
    """Migrate a test file to the new framework."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract the test function name
        match = re.search(r'def\s+(\w+)\s*\(\s*\)\s*:', content)
        if not match:
            return False, "Could not find test function"

        test_name = match.group(1)

        # Extract the test code
        match = re.search(r'return\s*{.*?"code"\s*:\s*"""(.*?)"""', content, re.DOTALL)
        if not match:
            return False, "Could not find test code"

        test_code = match.group(1).strip()

        # Extract configuration
        config = extract_config(content)

        # Extract or generate docstring
        docstring = f"Test for {test_name.replace('test_', '')}"
        match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if match:
            docstring = match.group(1).strip()

        # Clean up the test code
        cleaned_test_code = extract_test_code(test_code)

        # Determine utility needs
        include_timer = "benchmark_timer" in test_code
        include_results = "BENCHMARK TIMING DATA" in test_code
        include_packages = any(pkg in test_code for pkg in ["pip install", "subprocess.check_call"])

        # Generate migrated test
        migrated_content = MIGRATED_TEST_TEMPLATE.format(
            docstring=docstring,
            test_name=test_name,
            test_description=docstring,
            env_vars=config["env_vars"],
            single_run=config["single_run"],
            packages=config["packages"],
            is_info_test=config["is_info_test"],
            include_timer=include_timer,
            include_results=include_results,
            include_packages=include_packages,
            test_code=cleaned_test_code
        )

        # Determine output path
        if output_dir:
            base_name = os.path.basename(file_path)
            output_path = os.path.join(output_dir, f"{os.path.splitext(base_name)[0]}_migrated.py")
        else:
            output_path = f"{os.path.splitext(file_path)[0]}_migrated.py"

        # Write migrated test
        with open(output_path, 'w') as f:
            f.write(migrated_content)

        return True, f"Migrated test written to {output_path}"

    except Exception as e:
        return False, f"Error migrating test: {e}"

def main():
    parser = argparse.ArgumentParser(description="Migrate tests to the new optimized framework")
    parser.add_argument("files", nargs="+", help="Test files to migrate")
    parser.add_argument("--output-dir", "-o", help="Output directory for migrated tests")

    args = parser.parse_args()

    # Create output directory if specified and doesn't exist
    if args.output_dir and not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # Migrate each file
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue

        print(f"Migrating {file_path}...")
        success, message = migrate_test(file_path, args.output_dir)
        print(f"  {'Success' if success else 'Error'}: {message}")

if __name__ == "__main__":
    main()