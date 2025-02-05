from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from daytona_sdk import Daytona, DaytonaConfig, CreateWorkspaceParams
from dotenv import load_dotenv
import os

load_dotenv()

for key in ["OPENAI_API_KEY", "DAYTONA_API_KEY", "DAYTONA_SERVER_URL"]:
    if not os.getenv(key):
        raise ValueError(f"{key} not found in environment variables")

llm = OpenAI(temperature=0.2, max_tokens=1000)
code_chain = PromptTemplate(
    input_variables=["language", "task"],
    template="You are an expert {language} developer. Write clean, efficient, and well-documented code for the following task:\n\nTask: {task}\n\nPlease provide:\n1. A complete implementation\n2. Brief comments explaining key parts\n3. Example usage if applicable\n\nCode:"
) | llm

def generate_code(language: str, task: str):
    return code_chain.invoke({"language": language, "task": task})

def execute_in_sandbox(code: str):
    daytona = Daytona(config=DaytonaConfig(
        api_key=str(os.getenv("DAYTONA_API_KEY")),
        server_url=str(os.getenv("DAYTONA_SERVER_URL")),
        target="local"
    ))
    workspace = daytona.create(params=CreateWorkspaceParams(language="python"))
    try:
        response = workspace.process.code_run(code)
        return response.result if response.code == 0 else f"Error: {response.code} {response.result}"
    finally:
        daytona.remove(workspace)

if __name__ == "__main__":
    print("Code execution result:", execute_in_sandbox(
        generate_code("Python", "Create a function that takes a list of numbers and returns the moving average with a specified window size")
    ))
