import os
import openai

# Set API key
api_key = os.getenv("MISTRAL_API_KEY")

# Create a client
client = openai.OpenAI(api_key="f65U0dkcMyDs4JdCDS8acwwaAv4B1adM", base_url="https://api.mistral.ai/v1")

# Call the Mistral model
response = client.chat.completions.create(
    model="mistral-small-latest",
    messages=[{"role": "user", "content": "Explain quantum computing in simple terms."}]
)

# Print the response
print(response.choices[0].message.content)
