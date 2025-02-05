from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
import os

daytona = Daytona(
    config=DaytonaConfig(
        api_key=str(os.getenv("DAYTONA_API_KEY")),
        server_url=str(os.getenv("DAYTONA_SERVER_URL")),
        target="eu"
    )
)

# Create workspace parameters
params = CreateWorkspaceParams(
    language="python"
)

workspace = None
try:
    # Create a new workspace
    print("Creating workspace...")
    workspace = daytona.create(params)
    print("Workspace created successfully!")

    # Run a simple hello world command
    print("\nExecuting command...")
    response = workspace.process.exec('echo "Hello, World from Daytona!"')

    # Check the response
    if response.exit_code == 0:
        print("\nOutput:", response.result)
    else:
        print("\nError:", response.result)
        print("Exit code:", response.exit_code)

    # Alternative: Run Python code directly
    print("\nExecuting Python code...")
    code_response = workspace.process.code_run('print("Hello, World from Python!")')

    if code_response.exit_code == 0:
        print("\nOutput:", code_response.result)
    else:
        print("\nError:", code_response.result)
        print("Exit code:", code_response.exit_code)

except Exception as e:
    print(f"\nAn error occurred: {str(e)}")

finally:
    # Clean up by removing the workspace if it was created
    if workspace:
        print("\nCleaning up...")
        try:
            daytona.remove(workspace)
            print("Workspace removed!")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")