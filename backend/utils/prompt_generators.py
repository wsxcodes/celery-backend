import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def load_prompts() -> dict:

    with open("prompts/prompts.json", "r") as f:
        prompts = json.load(f)

    return prompts


def run_ai_completition(
        ai_client,
        prompt: dict,
        document_text=None,
        document_extra1=None,
        document_extra2=None,
        document_extra3=None,
        output_language="Czech",
        inject_date=False
        ):
    """
    Generate a smart summary for the given prompt text using the loaded template.
    """
    system_content = prompt["messages"][0]["content"].replace("{output_language}", output_language)
    user_template = prompt["messages"][1]["content"]

    if document_text:
        user_content = user_template.replace("{document_text}", document_text)
    else:
        user_content = user_template

    if document_extra1:
        user_content = user_content.replace("{document_extra1}", document_extra1)
    if document_extra2:
        user_content = user_content.replace("{document_extra2}", document_extra2)
    if document_extra3:
        user_content = user_content.replace("{document_extra3}", document_extra3)

    if inject_date:
        date_to_prompt = "Today is " + str(datetime.datetime.now().date())
        user_content = date_to_prompt + ". " + user_content

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
