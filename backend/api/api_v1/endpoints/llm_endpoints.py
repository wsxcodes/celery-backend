import logging
from typing import Dict
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from backend.decorators import log_endpoint
from backend.dependencies import ai_client
from fastapi import APIRouter

from backend.decorators import log_endpoint

logger = logging.getLogger(__name__)

router = APIRouter()


# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


router = APIRouter()


@router.get("/chat_completition")
@log_endpoint
async def chat_completion(
    system_message: str = Query(..., description="The system prompt"),
    user_message: str = Query(..., description="The user prompt"),
    model: str = Query(..., description="Model name, e.g. 'gpt-4.1'"),
    temperature: float = Query(0.5, ge=0.0, le=1.0, description="Sampling temperature"),
) -> Dict[str, Any]:
    """Chat completion endpoint."""
    try:
        response = ai_client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as e:
        logger.error("AI completion error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="AI service error")

    # pull out the generated message
    message_text = response.choices[0].message.content

    # token usage
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }
    logger.info(
        "Token usage - prompt: %d, completion: %d, total: %d",
        usage["prompt_tokens"],
        usage["completion_tokens"],
        usage["total_tokens"],
    )

    return {
        "status": "success",
        "message": message_text,
        "usage": usage,
    }

# @router.get("/chat_completition_streaming")
# @log_endpoint
# async def chat_completion_streaming() -> ??:
#     """Chat completion endpoint."""
#     # XXX tokens_spent should be added to the document metadata
#     return {
#         "status": "XXX",
#         "message": "TODO"
#     }
