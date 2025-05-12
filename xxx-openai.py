import os 
import json
from backend import config
from backend.utils import prompt_generators
from backend.utils.helpers import safe_request

from openai import AzureOpenAI


client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_version=config.OPENAI_API_VERSION
)

 
prompts = prompt_generators.load_prompts()



document = safe_request(
            request_type="GET",
            url=config.API_URL + "/api/v1/document/get/a699ac08-cd55-49b9-8aaf-cdc2b46e77b6",
            data={},
        )
raw_text = document.json()["raw_text"]


example_prompt = prompts["smart_summary"]

output_language = "Slovak"

response = client.chat.completions.create(
    model=example_prompt["model"],
    temperature=example_prompt["temperature"],
    messages=[
            {
                "role": "system",
                "content": example_prompt["messages"][0]["content"].replace("{output_language}", output_language)
            },
            {
                "role": "user",
                "content": example_prompt["messages"][0]["content"].replace("{document_text}", raw_text)
            }
        ],
    response_format=example_prompt["schema"]
)

response = response.choices[0].message
data = json.loads(response.content)

from pprint import pprint
pprint(data)
