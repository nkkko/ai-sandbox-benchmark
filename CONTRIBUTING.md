# Contributing to AI Sandbox Benchmark

First off, thanks for taking the time to contribute to AI Sandbox Benchmark! This document provides guidelines and instructions for contributing to this project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Setting Up Development Environment](#setting-up-development-environment)
  - [Development Workflow](#development-workflow)
- [How to Contribute](#how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Pull Requests](#pull-requests)
- [Creating New Tests](#creating-new-tests)
  - [Test Structure](#test-structure)
  - [Test Guidelines](#test-guidelines)
- [Integrating New Providers](#integrating-new-providers)
  - [Provider Interface](#provider-interface)
  - [Provider Guidelines](#provider-guidelines)
- [Style Guide](#style-guide)
  - [Python Style](#python-style)
  - [Documentation](#documentation)
- [Release Process](#release-process)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Setting Up Development Environment

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/ai-sandbox-benchmark.git
   cd ai-sandbox-benchmark
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node.js Dependencies**
   ```bash
   cd providers
   npm install
   cd ..
   ```

5. **Configure Environment Variables**
   - Create a `.env` file in the root directory with necessary API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   DAYTONA_API_KEY=your_daytona_api_key
   DAYTONA_SERVER_URL=your_daytona_server_url
   CSB_API_KEY=your_codesandbox_api_key
   E2B_API_KEY=your_e2b_api_key
   ```

### Development Workflow

1. **Create a New Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Test**
   - Make your code changes
   - Run relevant tests to ensure functionality:
     ```bash
     python comparator.py --tests your-test-id --providers local
     ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "Descriptive commit message"
   ```

4. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a Pull Request**
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your branch and provide a description of your changes

## How to Contribute

### Reporting Bugs

When reporting bugs, please include:
- Description of the bug
- Steps to reproduce
- Expected behavior
- Screenshots (if applicable)
- Environment information (OS, Python version, etc.)

Use the GitHub Issues feature with the "bug" label.

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:
- Clear description of the enhancement
- Rationale and use cases
- Any implementation ideas

Use the GitHub Issues feature with the "enhancement" label.

### Pull Requests

1. Follow the branching workflow described above
2. Update relevant documentation
3. Include test cases for new functionality
4. Ensure all tests pass before submitting
5. Reference any related issues in your PR description

## Creating New Tests

New tests help expand the benchmark's coverage of different aspects of sandbox environments.

### Test Structure

Create a new file in the `tests/` directory with the naming convention `test_your_test_name.py`. Use the template provided in `tests/test_template.py` as a starting point.

```python
from test_rule import TestRule

class YourTestClass(TestRule):
    id = "unique_test_id"  # Numeric or string identifier
    name = "Human-readable test name"
    description = "Detailed description of what the test evaluates"
    
    # Optional test properties
    single_run = False  # Set to True if test should only run once
    timeout = 60  # Timeout in seconds
    
    def get_code(self):
        # Return the code string to be executed in the sandbox
        return """
# Your test code here
import time
import sys

# Perform your test operations
result = "Success"

# Print the result (required for validation)
print(f"RESULT: {result}")
"""

    def validate_result(self, result):
        # Validate the result returned from the sandbox
        # Return True if valid, False otherwise
        return "Success" in result
```

### Test Guidelines

- **Independent Tests**: Each test should be self-contained and not rely on the state from other tests
- **Deterministic Results**: Tests should produce consistent results
- **Clear Validation**: Define clear success/failure criteria
- **Documented Code**: Include comments explaining complex operations
- **Resource Conscious**: Consider the resources required to run your test
- **Error Handling**: Include proper error handling in your test code

## Integrating New Providers

Adding support for new sandbox providers expands the utility of the benchmarking framework.

### Provider Interface

Create a new provider module in the `providers/` directory with the filename `your_provider_name.py`. Each provider should implement the following interface:

```python
async def execute(code, workspace_id=None, timeout=60, **kwargs):
    """
    Execute code in the sandbox provider.
    
    Args:
        code (str): The code to execute
        workspace_id (str, optional): Identifier for the workspace
        timeout (int): Execution timeout in seconds
        **kwargs: Additional provider-specific parameters
        
    Returns:
        dict: Result dictionary containing:
            - result (str): Output from code execution
            - creation_time (float): Time to create the workspace
            - execution_time (float): Time to execute the code
            - cleanup_time (float): Time to clean up resources
            - total_time (float): Total end-to-end time
            - success (bool): Whether execution was successful
            - error (str, optional): Error message if execution failed
    """
    # Implementation goes here
```

### Provider Guidelines

- **Proper Error Handling**: Catch and report errors appropriately
- **Resource Cleanup**: Always clean up resources, even in error cases
- **Timeout Handling**: Respect the timeout parameter
- **Detailed Metrics**: Track and report all required timing metrics
- **Configuration Options**: Support provider-specific configuration

## Style Guide

### Python Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Keep line length to a maximum of 100 characters
- Use snake_case for function names and variables
- Use CamelCase for class names
- Imports should be organized:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Use descriptive variable names

Example:
```python
import os
import time
from typing import Dict, List, Optional

import numpy as np
import requests

from metrics import calculate_statistics
from providers.utils import format_time


def process_results(results: List[Dict], normalize: bool = False) -> Dict:
    """
    Process benchmark results.
    
    Args:
        results: List of result dictionaries
        normalize: Whether to normalize values
        
    Returns:
        Processed results dictionary
    """
    # Implementation
```

### Documentation

- Use docstrings for all public functions, classes, and methods
- Follow Google style for docstrings
- Keep README.md up to date with new features and tests
- Update MIGRATION_GUIDE.md when introducing breaking changes
- Add comments for complex code sections

## Release Process

1. **Version Bump**: Update version in relevant files
2. **Changelog**: Update CHANGELOG.md with summary of changes
3. **Testing**: Ensure all tests pass
4. **Documentation**: Update documentation for new features
5. **Tag Release**: Create a Git tag for the new version
6. **Publish**: Push the tag and create a GitHub release

## Community

- Join discussions in GitHub Discussions
- Attend community meetings (if applicable)
- Share your usage of the benchmark in the wiki
- Help answer questions from other users

---

Thank you for contributing to AI Sandbox Benchmark! Your efforts help make this project better for everyone.