def test_list_directory():
    """List directory contents using bash ls command instead of Python."""
    return """
import subprocess

# Run the ls command in the home directory
result = subprocess.run(['ls', '-la', '/home'], capture_output=True, text=True)
print(result.stdout)
"""