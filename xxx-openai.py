import os 
import json
from backend import config
from backend.utils import prompt_generators
from backend.utils.helpers import safe_request

from openai import AzureOpenAI


ai_client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_version=config.OPENAI_API_VERSION
)

 
prompts = prompt_generators.load_prompts()

document_uuid = "edf60c87-27dc-4a19-a404-284f0424babc"

document = safe_request(
            request_type="GET",
            url=config.API_URL + f"/api/v1/document/get/{document_uuid}",
            data={},
        )
raw_text = document.json()["raw_text"]

output_language = "Slovak"

def run_ai_completition(prompt_text, output_language="Slovak"):
    """
    Generate a smart summary for the given prompt text using the loaded template.
    """
    system_content = example_prompt["messages"][0]["content"].replace("{output_language}", output_language)
    user_template = example_prompt["messages"][1]["content"]
    user_content = user_template.replace("{document_text}", prompt_text)
    response = ai_client.chat.completions.create(
        model=example_prompt["model"],
        temperature=example_prompt["temperature"],
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ],
        response_format=example_prompt["schema"]
    )
    message = response.choices[0].message
    return json.loads(message.content)

example_prompt = prompts["smart_summary"]


data = run_ai_completition(raw_text)

from pprint import pprint
pprint(data)
