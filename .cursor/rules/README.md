# Cursor Rules for AI Sandbox Benchmark

This directory contains custom rules for the [Cursor IDE](https://cursor.sh/) that help maintain coding standards and best practices for the AI Sandbox Benchmark project.

## Available Rules

### Benchmark Test Standards (`benchmark_test_standards.mdc`)

This rule helps maintain consistency in test implementation across the benchmarking tool. It enforces:

1. **Test Function Naming Convention** - All test functions should follow the pattern `test_<category>_<specific_test>` for consistency and easy identification.

2. **Test Docstring Required** - Every test function should have a detailed docstring explaining its purpose, inputs, and expected outputs.

3. **Test Return Metrics** - Test functions should return both the code to execute and the expected outputs for validation.

4. **Provider Compatibility Tag** - Tests should specify which sandbox providers they are compatible with using a `PROVIDERS_COMPATIBILITY` list.

5. **Test Complexity Indication** - Tests should indicate their complexity level ('simple', 'medium', or 'complex') to help with test selection and benchmarking.

6. **Test Timeout Specification** - Tests should specify their expected maximum runtime in seconds to prevent indefinite hangs.

### Python Code Standards (`python_code_standards.mdc`)

This rule enforces consistent Python code style and documentation practices:

1. **Function Docstring** - All public functions should have a docstring.

2. **Class Docstring** - All classes should have a docstring.

3. **Type Hints** - Functions should use type hints for parameters and return values.

4. **Async/Await Consistency** - Async functions should properly use await when calling other async functions.

5. **Error Handling** - Functions that could fail should include try-except blocks.

6. **Constants Naming** - Constants should be in UPPER_SNAKE_CASE.

7. **Imports Grouping** - Imports should be grouped: standard library, third-party, local.

### Python Style Guide (`python_style.mdc`)

This rule provides additional Python coding style guidelines:

1. **Function Docstring** - All public functions should have a docstring.

2. **Variable Naming Convention** - Variables should use snake_case naming.

3. **Line Length** - Lines should not exceed 100 characters.

4. **Class Naming Convention** - Classes should use PascalCase naming.

5. **Empty Line After Function** - Functions should be followed by an empty line.

6. **Import Order** - Standard library imports should come before third-party imports.

## How to Use

When working on the project, Cursor will automatically highlight any violations of these rules. The rules have different severity levels:

- **Warning**: Important standards to follow for consistency
- **Info**: Recommended practices that improve code quality

## MDC File Structure

Cursor rules files must be in the `.mdc` format with the following structure:

```
---
description: Brief description of the rule file
globs: ["*.py", "path/to/*.py"]  # Files to apply the rules to
alwaysApply: false               # Whether to always apply the rules
---
# Rule Title

```rule
id: rule-id
name: Rule Name
description: Description of the rule
pattern: Regular expression pattern
severity: warning|info|error
```

exclusions: ["path/to/excluded/*.py"]  # Files to exclude from rule application
```

## Extending Rules

To add new rules or modify existing ones, edit the corresponding MDC file. Make sure to follow the structure above, including the YAML frontmatter at the beginning of the file.

After making changes to rules, you may need to restart Cursor to see the updates take effect.