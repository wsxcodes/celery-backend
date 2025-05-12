from openai import AzureOpenAI

from backend import config

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
