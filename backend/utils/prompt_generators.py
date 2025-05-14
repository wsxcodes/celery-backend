import json
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def load_prompts() -> dict:

    with open("prompts/prompts.json", "r") as f:
        prompts = json.load(f)

    return prompts


def run_ai_completition(ai_client, prompt: dict, document_text=None, document_extra=None, output_language="Czech"):
    """
    Generate a smart summary for the given prompt text using the loaded template.
    """
    system_content = prompt["messages"][0]["content"].replace("{output_language}", output_language)
    user_template = prompt["messages"][1]["content"]

    if document_text:
        user_content = user_template.replace("{document_text}", document_text)
    else:
        user_content = user_template

    if document_extra:
        user_content = user_content.replace("{document_extra}", document_extra)

    if "schema" in prompt:
        response = ai_client.chat.completions.create(
            model=prompt["model"],
            temperature=prompt["temperature"],
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            response_format=prompt["schema"]
        )
        message = response.choices[0].message
        data = json.loads(message.content)
    else:
        response = ai_client.chat.completions.create(
            model=prompt["model"],
            temperature=prompt["temperature"],
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ]
        )
        message = response.choices[0].message.content
        data = {"message": message}

    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }
    data["usage"] = usage
    logger.info(f"Token usage - prompt: {usage['prompt_tokens']}, completion: {usage['completion_tokens']}, total: {usage['total_tokens']}")

    return data
