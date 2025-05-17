import json
import logging
from typing import Any, Dict, List

import tiktoken
from fastapi import APIRouter, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from backend.decorators import log_endpoint
from backend.dependencies import ai_client
from backend.utils.helpers import update_tokens_spent_async

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
    # XXX TODO check that the document exists using check_exists endpoint, otherwise refuse the request
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

    # Record token usage asynchronously
    await update_tokens_spent_async(
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
    # XXX TODO check that the document exists using check_exists endpoint, otherwise refuse the request
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

    async def event_generator():
        # Initialize encoder and token counters
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        prompt_tokens = sum(len(enc.encode(msg)) for msg in [system_message, user_message])
        completion_chunks: List[str] = []

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
            completion_chunks.append(content)
            yield f"data: {json.dumps({'content': content})}\n\n"

        # Compute token usage manually
        completion_tokens = sum(len(enc.encode(c)) for c in completion_chunks)
        total_tokens = prompt_tokens + completion_tokens
        logger.info("Token usage - prompt: %d, completion: %d, total: %d", prompt_tokens, completion_tokens, total_tokens)

        # Record token usage asynchronously after streaming completes
        try:
            await update_tokens_spent_async(
                document_uuid=document_uuid,
                add_tokens_spent=total_tokens,
            )
            logger.info("Tokens spent updated for document %s, total tokens: %d", document_uuid, total_tokens)
        except Exception as e:
            logger.error("Failed to update tokens for document %s: %s", document_uuid, e)
        yield "data: [DONE]\n\n"

    return EventSourceResponse(
        event_generator(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
