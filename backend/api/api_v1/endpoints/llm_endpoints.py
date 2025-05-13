import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from backend.decorators import log_endpoint
from backend.dependencies import ai_client
from backend.utils.helpers import update_tokens_spent

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
    document_uuid: str,
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

    # Record token usage
    update_tokens_spent(
        document_uuid=document_uuid,
        add_tokens_spent=usage["total_tokens"],
    )
    logger.info("Tokens spent updated for document %s", document_uuid)

    return {
        "status": "success",
        "message": message_text,
        "usage": usage,
    }


@router.get("/chat_completition_streaming")
@log_endpoint
async def chat_completion_streaming(
    document_uuid: str,
    system_message: str = Query(..., description="The system prompt"),
    user_message: str = Query(..., description="The user prompt"),
    model: str = Query(..., description="Model name, e.g. 'gpt-4.1'"),
    temperature: float = Query(0.5, ge=0.0, le=1.0, description="Sampling temperature"),
) -> EventSourceResponse:
    """Chat completion streaming endpoint."""
    try:
        stream = ai_client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            stream=True,
        )
    except Exception as e:
        logger.error("AI streaming error: %s", e, exc_info=True)
        raise HTTPException(status_code=502, detail="AI service error")

    def event_generator():
        for chunk in stream:
            # skip chunks without choices or delta
            choices = getattr(chunk, "choices", None)
            if not choices:
                continue
            choice = choices[0]
            delta = getattr(choice, "delta", None)
            content = getattr(delta, "content", None)
            if not content:
                continue
            yield f"data: {json.dumps({'content': content})}\n\n"
        yield "data: [DONE]\n\n"

    # XXX record the token usage in the database

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
