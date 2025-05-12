import logging

from openai import AzureOpenAI

from backend import config
from backend.utils import prompt_generators
from backend.utils.helpers import safe_request
from backend.utils.prompt_generators import run_ai_completition
from workers.analysis_worker import update_tokens_spent

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------------------------------------------------------

document_uuid = "6a61c4da-6d86-4de9-814d-349909559cfa"

# -----------------------------------------------------------------------------------------------------------------------------


ai_client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_version=config.OPENAI_API_VERSION
)

prompts = prompt_generators.load_prompts()

# document = safe_request(
#             request_type="GET",
#             url=config.API_URL + f"/api/v1/document/get/{document_uuid}",
#             data={},
#         )
# raw_text = document.json()["raw_text"]

output_language = "Slovak"
tokens_spent = 0

# -----------------------------------------------------------------------------------------------------------------------------

# # Run the smart summary prompt
# smart_summary = prompts["smart_summary"]
# data = run_ai_completition(ai_client=ai_client, prompt=smart_summary, document_text=raw_text, output_language="Slovak")

# usage = data.get("usage")
# tokens_spent += usage["total_tokens"]

# logger.info("Saving smart summary to database")
# safe_request(
#     request_type="PATCH",
#     url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
#     data={
#         "ai_category": data["top_category"],
#         "ai_sub_category": data["sub_category"],
#         "ai_summary_short": data["summary_short"],
#         "ai_summary_long": data["summary_long"]
#     }
# )

# # Record the tokens spent
# update_tokens_spent(
#     document_uuid=document_uuid,
#     add_tokens_spent=tokens_spent
# )

# -----------------------------------------------------------------------------------------------------------------------------

# Example simple prompt

simple_prompt = prompts["example_prompt_simple"]
data = run_ai_completition(ai_client=ai_client, prompt=simple_prompt, document_text="", output_language="Slovak")

usage = data.get("usage")
tokens_spent += usage["total_tokens"]

print(data)
print(usage)
