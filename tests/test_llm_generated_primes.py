# tests/test_llm_generated_primes.py

import os
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate

# Module-level variable to cache the generated code
GENERATED_CODE = None

def test_llm_generated_calculate_primes():
    """
    Generates Python code to calculate the first 10 prime numbers,
    compute their sum and average, and print the results with
    appropriate formatting. The code is generated once and reused
    across multiple test executions.
    """
    global GENERATED_CODE
    if GENERATED_CODE is None:
        task = """Write a Python program that:
        1. Calculates the first 10 prime numbers
        2. Computes their sum and average
        3. Prints the results with appropriate formatting
        """
        try:
            # Initialize the OpenAI LLM with desired parameters
            llm = OpenAI(temperature=0.2, max_tokens=500)

            # Define the prompt template
            prompt = PromptTemplate(
                input_variables=["task"],
                template="Write Python code for the following task:\n\n{task}\n\nCode:"
            )

            # Generate the code using the LLM
            generated_code = llm(prompt.format(task=task))

            # Cache the generated code
            GENERATED_CODE = generated_code.strip()
            print("LLM Generated Code:\n", GENERATED_CODE)  # Optional: Remove or comment out in production

        except Exception as e:
            print(f"Error generating code with LLM: {e}")
            raise
    return GENERATED_CODE