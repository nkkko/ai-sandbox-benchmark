# Contributing to AI Sandbox Benchmark

We welcome contributions from the community! This document provides guidelines and instructions for contributing to the AI Sandbox Benchmark project.

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

## 📄 License

By contributing to AI Sandbox Benchmark, you agree that your contributions will be licensed under the project's [Apache 2.0 License](LICENSE).

---

Thank you for contributing to the AI Sandbox Benchmark project! Your participation helps make this tool more robust and valuable for the community.