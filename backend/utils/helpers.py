import logging
import re

import requests

logger = logging.getLogger(__name__)


def perform_request(request_type: str, url: str, data: dict, headers: dict = None) -> requests.Response:
    try:
        logger.info(f"Performing {request_type} request to {url} with data {data} and headers {headers}")

        if request_type.upper() == "GET":
            response = requests.get(url, params=data, headers=headers)
        elif request_type.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif request_type.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif request_type.upper() == "DELETE":
            response = requests.delete(url, json=data, headers=headers)
        elif request_type.upper() == "PATCH":
            response = requests.patch(url, json=data, headers=headers)
        else:
            raise ValueError(f"Unsupported request type: {request_type}")

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


def safe_request(*, request_type, url, data, headers=None):
    try:
        response = perform_request(request_type=request_type, url=url, data=data, headers=headers)
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


def construct_docu_info_in_text(document) -> str:
    """
    Construct a document information string from the document metadata.
    """
    doc_info = (
        f"Document Name: {document.filename}\n"
        f"Document Size: {document.file_size} bytes\n"
        f"Document Category: {document.ai_category}\n"
        f"Document Sub-Category: {document.ai_sub_category}\n"
        # f"AI proposed document AI analysis criteria: {document.ai_analysis_criteria}\n"
        # f"AI proposed things to look at: {document.ai_features_and_insights}\n"
        # f"AI proposed alerts and actions: {document.ai_alerts_and_actions}\n"
        f"\n\n"
        f"Document Raw Text:\n{document.document_raw_text}\n"
    )
    return doc_info
