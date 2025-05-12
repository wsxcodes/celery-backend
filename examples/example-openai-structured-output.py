import os 
from backend import config

from pydantic import BaseModel
from openai import AzureOpenAI


client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_version=config.OPENAI_API_VERSION
)

# ------------------ Pydantic SCHEMA example ------------------

class HelloWorld(BaseModel):
    text: str
    number: int

completion = client.beta.chat.completions.parse(
    model="gpt-4.1",
    temperature=0.5,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user",   "content": "Say hello world and number 1."}
    ],
    response_format=HelloWorld
)

# parsed object
result = completion.choices[0].message.parsed
print(result)

# raw JSON string if you need it
print(completion.choices[0].message.content)


# ------------------ JSON SCHEMA example ------------------

schema = {
    "type": "json_schema",
    "json_schema": {
        "name": "SimpleSchema",       # <— you must give it a name
        "strict": True,               # <— strict belongs here
        "schema": {                   # <— your real JSON Schema goes here
            "type": "object",
            "properties": {
                "text":   {"type": "string"},
                "number": {"type": "integer"}
            },
            "required": ["text", "number"],
            "additionalProperties": False
        }
    }
}

response = client.chat.completions.create(
    model="gpt-4.1",
    temperature=0.5,
    messages=[
        {"role": "system",  "content": "You are a helpful assistant."},
        {"role": "user",    "content": "Say hello world and number 1."}
    ],
    response_format=schema
)

# parsed object
result = completion.choices[0].message.parsed
print(result)

# raw JSON string if you need it
print(completion.choices[0].message.content)
