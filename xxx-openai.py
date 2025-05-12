# Install the latest OpenAI SDK
# pip install --upgrade openai

import os
from backend import config

from openai import AzureOpenAI

# Initialize the OpenAI client
client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_version=config.OPENAI_API_VERSION
)

# Create a chat completion
response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a joke."}
    ]
)

# Print the assistant's reply
print(response.choices[0].message.content)

# Example 2: Requesting structured JSON output
response_json = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": (
            "You are a JSON generator. "
            "Always respond with valid JSON following this schema: "
            '{"joke": "string", "length": "integer"}'
        )},
        {"role": "user", "content": "Tell me a joke."}
    ]
)
structured_output = response_json.choices[0].message.content
print("Structured JSON response:", structured_output)
