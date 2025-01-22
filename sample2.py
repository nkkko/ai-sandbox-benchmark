import daytona_sdk
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize Daytona client
daytona = daytona_sdk.Daytona(
    config=daytona_sdk.DaytonaConfig(
        api_key=str(os.getenv("DAYTONA_API_KEY")),
        server_url=str(os.getenv("DAYTONA_SERVER_URL")),
        target="local"
    )
)

# Create workspace
workspace = daytona.create()

# Start a simple server in background
server_code = """
from http.server import HTTPServer, SimpleHTTPRequestHandler
server = HTTPServer(('0.0.0.0', 5000), SimpleHTTPRequestHandler)
print('Server running on port 5000...')
server.serve_forever()
"""
workspace.process.code_run(server_code)

# Execute port forwarding command
forward_response = workspace.process.exec(
    "daytona forward 5000 ai-enablement-stack ai-enablement-stack --public"
)
print("Port forwarding status:", forward_response.result)

# Keep the script running to maintain the server
try:
    print("Server is running.")
    print("Press Ctrl+C to stop...")
    while True:
        pass
except KeyboardInterrupt:
    print("\nStopping server and cleanup...")

# Cleanup
daytona.remove(workspace)