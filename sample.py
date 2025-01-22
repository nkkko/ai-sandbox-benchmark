import daytona_sdk

daytona = daytona_sdk.Daytona(
    config=daytona_sdk.DaytonaConfig(
        api_key=str(os.getenv("DAYTONA_API_KEY")),
        server_url=str(os.getenv("DAYTONA_SERVER_URL")),
        target="local"
    )
)

workspace = daytona.create()

code = """
print("Sum of 3 and 4 is " + str(3 + 4))
"""

response = workspace.process.code_run(code)
print(response.result)

daytona.remove(workspace)