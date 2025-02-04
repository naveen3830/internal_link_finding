import os
from dotenv import load_dotenv

# Print current directory
print(f"Current directory: {os.getcwd()}")

# Load .env file
load_dotenv()

# Get API key
api_key = os.getenv('GROQ_API_KEY')

# Print result (be careful not to share the actual key)
if api_key:
    print(f"API key loaded successfully! First 4 chars: {api_key[:4]}***")
else:
    print("No API key found!")

# List all environment variables (be careful with sensitive info)
print("\nAll environment variables:")
for key, value in os.environ.items():
    if 'API' in key:
        print(f"{key}: {'*' * len(value)}")