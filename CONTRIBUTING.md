# Contributing to AI Sandbox Benchmark

We welcome contributions from the community! This document provides guidelines and instructions for contributing to the AI Sandbox Benchmark project.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## 🚀 Ways to Contribute

There are many ways to contribute to the AI Sandbox Benchmark project:

- **Add New Tests:** Extend the test suite with new scenarios to evaluate sandbox performance
- **Integrate Providers:** Connect additional sandbox environments to broaden the comparison scope
- **Improve Documentation:** Help enhance the clarity and usability of the project guides
- **Optimize Existing Tests:** Improve performance of current tests
- **Fix Bugs:** Help identify and fix issues in the codebase
- **Add Features:** Implement new features to enhance the benchmark functionality

## 📋 Contribution Process

### 1. Setting Up Your Development Environment

1. **Fork the Repository**

   Click the "Fork" button at the top right of the repository page to create your own fork.

2. **Clone Your Fork**

   ```bash
   git clone https://github.com/yourusername/ai-sandbox-benchmark.git
   cd ai-sandbox-benchmark
   ```

3. **Set Up a Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Install Node.js Dependencies (for CodeSandbox Service)**

   ```bash
   cd providers
   npm install
   cd ..
   ```

6. **Configure Environment Variables**
   - Create a `.env` file in the root directory with necessary API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   DAYTONA_API_KEY=your_daytona_api_key
   DAYTONA_SERVER_URL=your_daytona_server_url
   CSB_API_KEY=your_codesandbox_api_key
   E2B_API_KEY=your_e2b_api_key
   ```

### 2. Making Changes

1. **Create a New Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**

   - Add new tests in the `tests/` directory
   - Integrate new providers in the `providers/` directory
   - Update documentation as needed
   - Follow the existing code style and patterns

3. **Test Your Changes**

   Run the benchmark tool to ensure your changes work as expected:

   ```bash
   python benchmark.py
   ```

### 3. Submitting Your Contribution

1. **Commit Your Changes**

   ```bash
   git commit -m "Add your descriptive commit message"
   ```

2. **Push to Your Fork**

   ```bash
   git push origin feature/your-feature-name
   ```

3. **Open a Pull Request**

   Go to the original repository and create a pull request from your forked branch.
   
   In your pull request description, please include:
   - A clear explanation of what your changes do
   - Any related issues that your PR addresses
   - If applicable, screenshots or examples

## 📝 Contribution Guidelines

### Code Style

- Follow the existing code style in the project
- Use snake_case for functions and variables, CamelCase for classes
- Add type hints to your Python code
- Include docstrings for public functions and classes

### Test Guidelines

When adding new tests:

1. Follow the template in `tests/test_template.py`
2. Ensure your test is well-documented with clear docstrings
3. Make sure your test works with all providers
4. Include a description of what your test measures in the test's docstring

### Provider Integration

When adding a new provider:

1. Create a new Python file in the `providers/` directory
2. Implement the required interface matching existing providers
3. Update the provider documentation in `providers/README.md`
4. Ensure proper resource cleanup in finally blocks

## 🧪 Testing Your Changes

Before submitting your pull request, make sure that:

1. Your code runs without errors
2. Your changes don't break existing functionality
3. You've tested across multiple providers if applicable

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

## Test Structure

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
## 📄 License

By contributing to AI Sandbox Benchmark, you agree that your contributions will be licensed under the project's [Apache 2.0 License](LICENSE).

---

Thank you for contributing to the AI Sandbox Benchmark project! Your participation helps make this tool more robust and valuable for the community.