import daytona_sdk

daytona = daytona_sdk.Daytona(
    config=daytona_sdk.DaytonaConfig(
        api_key="YTZjM2I1NDgtODE3My00NDZmLWIwOWQtMDg0YjAwZTZjYTQ3",
        server_url="http://147.28.196.237:3986",
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