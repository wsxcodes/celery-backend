import logging
import re

import httpx
import requests

from backend import config

logger = logging.getLogger(__name__)


def perform_request(request_type: str, url: str, data: dict) -> requests.Response:
    try:
        logger.info(f"Performing {request_type} request to {url} with data {data}")
        parsed_url = requests.utils.urlparse(url)
        logger.info(f"Parsed URL: {parsed_url.geturl()}")
        if parsed_url.port is None:
            logger.warning("No port specified in URL, defaulting to port 80 or 443 depending on scheme")

        if request_type.upper() == "GET":
            response = requests.get(url, params=data)
        elif request_type.upper() == "POST":
            response = requests.post(url, json=data)
        elif request_type.upper() == "PUT":
            response = requests.put(url, json=data)
        elif request_type.upper() == "DELETE":
            response = requests.delete(url, json=data)
        elif request_type.upper() == "PATCH":
            response = requests.patch(url, json=data)
        else:
            raise ValueError(f"Invalid request_type: {request_type}")

        response.raise_for_status()
        return response
    except requests.HTTPError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
        raise
    except requests.RequestException as e:
        logger.error(f"Error occurred: {str(e)}")
        raise
    except ValueError as e:
        logger.error(str(e))
        raise


def safe_request(*, request_type, url, data):
    try:
        response = perform_request(request_type=request_type, url=url, data=data)
        response.raise_for_status()
        return response
    except Exception as e:
        msg = ""
        if hasattr(e, "response") and e.response is not None:
            try:
                msg = e.response.json().get("message") or e.response.text
            except Exception:
                msg = e.response.text
        logger.error(f"API call failed: {e} - {msg}")
        return None


def format_analysis(text: str) -> str:
    """
    Convert a plain-text analysis plan into HTML structure.
    Expects:
      - A start statement, bullet points prefixed with ' - ', and an optional closing statement.
    """
    # Regex to extract bullet points at start of lines prefixed by '- '
    bullet_pattern = re.compile(r"(?m)^-\s+(.+)$")
    bullets = bullet_pattern.findall(text)
    matches = list(bullet_pattern.finditer(text))

    # Extract start statement (everything before the first bullet)
    if matches:
        start = text[:matches[0].start()].strip()
        last_end = matches[-1].end()
        closing = text[last_end:].strip()
    else:
        start = text.strip()
        closing = ""

    # Build HTML
    html = []
    html.append('<p class="text-gray-300 text-sm">')
    html.append(f'  {start}')
    html.append('</p>')
    if bullets:
        html.append('<ul class="list-disc list-inside text-gray-300 text-sm space-y-1">')
        for itm in bullets:
            html.append(f'  <li>{itm.strip()}</li>')
        html.append('</ul>')
    if closing:
        html.append('<p class="text-gray-300 text-sm mt-2">')
        html.append(f'  {closing}')
        html.append('</p>')

    return "\n".join(html)


def update_tokens_spent(document_uuid: str, add_tokens_spent: int) -> bool:
    logger.info(f"Updating tokens_spent for document {document_uuid} by {add_tokens_spent}")
    # Fetch current metadata
    response = safe_request(
        request_type="GET",
        url=config.API_URL + f"/api/v1/document/get/{document_uuid}",
        data={}
    )
    if not response or response.status_code != 200:
        logger.error(f"Failed to fetch metadata for document {document_uuid}")
        return False

    metadata = response.json()
    current = metadata.get("analysis_cost", 0)
    new_total = current + add_tokens_spent

    # Update metadata with new token total
    update_resp = safe_request(
        request_type="PATCH",
        url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
        data={"analysis_cost": new_total}
    )
    if update_resp and getattr(update_resp, 'status_code', None) == 200:
        logger.info(f"analysis_cost updated to {new_total} for document {document_uuid}")
    else:
        logger.error(f"Failed to update analysis_cost for document {document_uuid}")

    return True


async def update_tokens_spent_async(document_uuid: str, add_tokens_spent: int) -> bool:
    logger.info(f"Updating tokens_spent asynchronously for document {document_uuid} by {add_tokens_spent}")
    try:
        async with httpx.AsyncClient() as client:
            # Fetch current metadata
            get_url = config.API_URL + f"/api/v1/document/get/{document_uuid}"
            response = await client.get(get_url)
            response.raise_for_status()
            metadata = response.json()
            current = metadata.get("analysis_cost", 0)
            new_total = current + add_tokens_spent

            # Update metadata with new token total
            patch_url = config.API_URL + f"/api/v1/document/metadata/{document_uuid}"
            update_resp = await client.patch(patch_url, json={"analysis_cost": new_total})
            update_resp.raise_for_status()

        logger.info(f"analysis_cost updated to {new_total} for document {document_uuid}")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {str(e)}")
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
    return False
