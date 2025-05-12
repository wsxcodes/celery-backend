import datetime
import logging
import random
import time

from openai import AzureOpenAI

from backend import config
from backend.utils import prompt_generators
from backend.utils.helpers import safe_request

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

ai_client = AzureOpenAI(
    azure_endpoint=config.AZURE_OPENAI_ENDPOINT,
    api_version=config.OPENAI_API_VERSION
)

prompts = prompt_generators.load_prompts()


# XXX TODO output_language

# XXX TODO update "ai_expires" field in the database when applicable

# XXX extract entities, e.g. people, organizations, locations, full names, etc.

# XXX detect expiry dates, renewal clauses, trial periods - also update "ai_expires" field in the database


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


def main():
    while True:
        logger.info("Querying pending documents for analysis")
        pending_document = safe_request(
            request_type="GET",
            url=config.API_URL + "/api/v1/document/list/pending?limit=1",
            data={},
        )
        if not pending_document:
            time.sleep(1)
            continue

        pending_documents = pending_document.json()

        if pending_documents:

            tokens_spent = 0

            document_uuid = pending_documents[0]["uuid"]
            customer_id = pending_documents[0]["customer_id"]
            logger.info(f"Document to analyze: {document_uuid}")

            logger.info("Starting analysis")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"analysis_status": "processing", "analysis_started_at": datetime.datetime.now().isoformat()},
            )

            # Request document preview
            logger.info("Requesting document preview")
            preview_response = safe_request(
                request_type="GET",
                url=config.API_URL + f"/api/v1/utils/generate-file-preview?uuid={document_uuid}",
                data={},
            )

            if preview_response is None:
                logger.info("Preview generation request failed; skipping metadata update")
                continue

            if preview_response.status_code == 400:
                logger.info("Preview generation returned 400; skipping metadata update")
                continue

            if preview_response.status_code == 200:
                preview_path = preview_response.json()
                logger.info(f"Preview path: {preview_path}")

                logger.info("Updating document data")
                safe_request(
                    request_type="PATCH",
                    url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                    data={"file_preview": preview_path},
                )

            # Extract text from the document
            logger.info("Extracting text from document")
            raw_text = safe_request(
                request_type="GET",
                url=config.API_URL + f"/api/v1/utils/extract-text-from-file?uuid={document_uuid}",
                data={},
            )
            raw_text = raw_text.json()

            # Save the extracted text to the database
            logger.info("Saving extracted text to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"raw_text": raw_text},
            )

            # Get customer info
            customer = safe_request(
                request_type="GET",
                url=config.API_URL + f"/api/v1/customer/{customer_id}",
                data={}
            )
            output_language = customer.json().get("output_language", "English")
            logger.info(f"Customer output language: {output_language}")

            # XXX TODO Mark off AI Alert
            logger.info("Marking document as processed")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"ai_alert": "insights_available"},
            )
            logger.info("Analysis completed successfully")

            # XXX TEMP delay for testing
            # time.sleep(10)

            # XXX TODO do the category as the very last step

            # Update document analysis_cost
            update_tokens_spent(document_uuid=document_uuid, add_tokens_spent=tokens_spent)

            # Mark document as processed, update the cost
            logger.info("Marking document as processed")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={
                    "analysis_status": "processed",
                    "analysis_completed_at": datetime.datetime.now().isoformat(),
                    "health_score": random.randint(85, 95),  # XXX TODO calculate the health score
                }
            )
            logger.info("Analysis completed successfully")

        else:
            logger.info("No pending documents found")

        time.sleep(0.5)


if __name__ == "__main__":
    logger.info("Analysis worker started")
    main()
