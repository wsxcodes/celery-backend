import json


def load_prompts() -> dict:

    with open("prompts/prompts.json", "r") as f:
        prompts = json.load(f)

    return prompts
