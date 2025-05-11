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
