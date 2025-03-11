def test_llm_generated_primes():
    return """import os
from langchain.prompts import PromptTemplate
import time

def generate_prime_calculation_code():
    # Try to load from .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("Note: python-dotenv not available, checking environment variables directly")
    
    # First check for Anthropic API key
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        # Check for OPENAI API key as fallback
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            # Try to read from .env file manually as a fallback, check multiple locations
            potential_paths = ['.env', '/home/daytona/.env', '../.env']
            for env_path in potential_paths:
                try:
                    print(f"Checking for API keys in {env_path} file...")
                    with open(env_path, 'r') as f:
                        for line in f:
                            # Try to find either Anthropic or OpenAI key
                            if line.startswith('ANTHROPIC_API_KEY='):
                                key_name = "ANTHROPIC_API_KEY"
                                key_value = line.strip().split('=', 1)[1]
                            elif line.startswith('OPENAI_API_KEY='):
                                key_name = "OPENAI_API_KEY"
                                key_value = line.strip().split('=', 1)[1]
                            else:
                                continue
                                
                            # Remove quotes if present
                            if (key_value.startswith("'") and key_value.endswith("'")) or \
                               (key_value.startswith('"') and key_value.endswith('"')):
                                key_value = key_value[1:-1]
                            
                            # Remove any whitespace, newlines or extra characters
                            key_value = key_value.strip()
                            
                            # Store the key in environment
                            os.environ[key_name] = key_value
                            print(f"Key prefix: {key_value[:7]}...")  # Print just the prefix for debugging
                            print(f"Successfully loaded {key_name} from {env_path} file (length: {len(key_value)})")
                            
                            # If we found an Anthropic key, prefer it
                            if key_name == "ANTHROPIC_API_KEY":
                                anthropic_key = key_value
                            else:
                                openai_key = key_value
                except Exception as e:
                    print(f"Error reading {env_path} file: {e}")
            
            # If we still don't have either key, report error
            if not anthropic_key and not openai_key:
                print("ERROR: Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY found")
                return "print('Error: Missing API keys')"
        else:
            print(f"Found OPENAI_API_KEY environment variable (length: {len(openai_key)})")
    else:
        print(f"Found ANTHROPIC_API_KEY environment variable (length: {len(anthropic_key)})")
    
    task = '''Write a Python program that:
    1. Calculates the first 10 prime numbers
    2. Computes their sum and average
    3. Prints the results with appropriate formatting
    '''
    
    try:
        # Try Anthropic first if available
        if anthropic_key:
            try:
                print(f"Using Anthropic API key with prefix: {anthropic_key[:7]}... (length: {len(anthropic_key)})")
                
                # Try to install required packages if not available
                try:
                    from langchain_anthropic import ChatAnthropic
                except ImportError:
                    print("langchain-anthropic not available, installing...")
                    import sys, subprocess
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-anthropic"])
                    time.sleep(1)  # Give a moment for the install to complete
                    from langchain_anthropic import ChatAnthropic
                
                # Initialize the Anthropic LLM
                print("Initializing Anthropic Claude...")
                llm = ChatAnthropic(model="claude-3-haiku-20240307")
                
                # Define the prompt
                prompt = PromptTemplate(
                    input_variables=["task"],
                    template="Write Python code for the following task:\\n\\n{task}\\n\\nCode:"
                )
                
                # Generate the code using the LLM
                print("Calling Anthropic API...")
                result = llm.invoke(prompt.format(task=task))
                generated_code = result.content
                print("Successfully received response from Anthropic API")
                return generated_code.strip()
            except Exception as e:
                print(f"Error with Anthropic API: {e}")
                print("Falling back to OpenAI API if available...")
                # No need to include traceback here to keep output cleaner
                # If we have OpenAI key, we'll try that next
                if not openai_key:
                    import traceback
                    print(f"Error details: {traceback.format_exc()}")
                    return f"print('Error generating code with Anthropic: {str(e)}')"
        
        # Try OpenAI if no Anthropic key or if Anthropic failed
        if openai_key:
            print(f"Using OpenAI API key with prefix: {openai_key[:7]}... (length: {len(openai_key)})")
            
            try:
                from langchain_openai import OpenAI
            except ImportError:
                print("langchain-openai not available, installing...")
                import sys, subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain-openai"])
                time.sleep(1)  # Give a moment for the install to complete
                from langchain_openai import OpenAI
            
            # Initialize the OpenAI LLM with desired parameters
            llm = OpenAI(temperature=0.2, max_tokens=500)
            
            # Define the prompt template
            prompt = PromptTemplate(
                input_variables=["task"],
                template="Write Python code for the following task:\\n\\n{task}\\n\\nCode:"
            )
            
            # Generate the code using the LLM
            print("Calling OpenAI API...")
            generated_code = llm.invoke(prompt.format(task=task))
            print("Successfully received response from OpenAI API")
            return generated_code.strip()
        else:
            print("No API keys available for LLM access")
            return "print('Error: No valid API keys available')"
    except Exception as e:
        print(f"Error generating code: {e}")
        # Include more details about the error
        import traceback
        print(f"Error details: {traceback.format_exc()}")
        return f"print('Error generating code: {str(e)}')"

# Generate the code
print("Generating code with LLM...")
llm_code = generate_prime_calculation_code()
print("\\nLLM Generated Code:")
print(llm_code)

# Extract code from potential markdown formatting and execute it
try:
    print("\\nExecuting generated code:")
    # Check if the code is wrapped in markdown code blocks
    if '```python' in llm_code or '```' in llm_code:
        # Extract just the code part from markdown
        import re
        code_blocks = re.findall(r'```(?:python)?(.*?)```', llm_code, re.DOTALL)
        if code_blocks:
            # Use the first code block
            clean_code = code_blocks[0].strip()
            print("Extracted code from markdown formatting")
            exec(clean_code)
        else:
            # Fallback if regex didn't match but there are backticks
            print("Could not extract code block, trying direct execution")
            exec(llm_code)
    else:
        # Direct execution if no markdown detected
        exec(llm_code)
except Exception as e:
    print(f"Error executing generated code: {e}")
"""