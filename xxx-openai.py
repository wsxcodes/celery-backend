import os 
import json
from backend import config
from backend.utils import prompt_generators
from backend.utils.prompt_generators import run_ai_completition
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



example_prompt = prompts["smart_summary"]


data = run_ai_completition(ai_client=ai_client, prompt=example_prompt, document_text=raw_text, output_language="Slovak")

from pprint import pprint
pprint(data)
