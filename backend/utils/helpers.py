import re
import logging

import requests

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
    Convert a plain-text analysis plan into the desired HTML structure.
    Expects:
      - Text containing a start statement, bullet points prefixed with '- ', and a closing statement.
    """
    # Split into head (start + bullets) and closing based on '---'
    parts = text.split('---', 1)
    head = parts[0].strip()
    closing = parts[1].strip() if len(parts) > 1 else ''

    # Find all numbered bold headings
    section_pattern = re.compile(r"\*\*\s*(\d+)\.\s*(.*?)\*\*")
    matches = list(section_pattern.finditer(head))
    # Extract start statement (everything before the first section heading)
    if matches:
        start = head[:matches[0].start()].strip()
    else:
        start = head
    sections = []
    for i, m in enumerate(matches):
        # Extract heading text
        heading_text = f"{m.group(1)}. {m.group(2)}"
        # Determine the text range for items under this heading
        start_idx = m.end()
        end_idx = matches[i+1].start() if i+1 < len(matches) else len(head)
        items_block = head[start_idx:end_idx].strip()
        # Split on ' - ' to get individual items
        items = [itm.strip() for itm in items_block.split(' - ') if itm.strip()]
        # Remove any leading hyphens
        items = [re.sub(r'^-+\s*', '', itm) for itm in items]
        sections.append((heading_text, items))

    # Convert '**bold**' markdown in start and closing only
    bold_pattern = re.compile(r"\*\*(.*?)\*\*")
    start = bold_pattern.sub(r"<b>\1</b>", start)
    closing = bold_pattern.sub(r"<b>\1</b>", closing)

    # Build HTML
    html = []
    html.append('<p class="text-gray-300 text-sm">')
    html.append(f'  {start}')
    html.append('</p>')
    for heading_text, items in sections:
        # Heading line with two breaks before and after
        html.append(f'<br/><b>{heading_text}</b><br/>')
        html.append('<ul class="list-disc list-inside text-gray-300 text-sm space-y-1">')
        for itm in items:
            html.append(f'  <li>{itm}</li>')
        html.append('</ul>')
    html.append('<p class="text-gray-300 text-sm mt-2">')
    html.append(f'  {closing}')
    html.append('</p>')
    return "\n".join(html)
