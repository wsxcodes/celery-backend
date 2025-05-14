import datetime
import json
import logging
import random
import time

from backend import config
from backend.dependencies import ai_client
from backend.utils import prompt_generators
from backend.utils.helpers import safe_request, update_tokens_spent
from backend.utils.prompt_generators import run_ai_completition

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

prompts = prompt_generators.load_prompts()


# XXX TODO retry policy

# XXX TODO update "ai_expires" field in the database when applicable

# XXX detect expiry dates, renewal clauses, trial periods - also update "ai_expires" field in the database


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

            # -----------------------------------------------------------------------------------------------------------------------------
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

            # -----------------------------------------------------------------------------------------------------------------------------
            # Extract text from the document

            logger.info("Extracting text from document")
            raw_text = safe_request(
                request_type="GET",
                url=config.API_URL + f"/api/v1/utils/extract-text-from-file?uuid={document_uuid}",
                data={},
            )
            raw_text = raw_text.json()

            # -----------------------------------------------------------------------------------------------------------------------------
            # Save the extracted text to the database

            logger.info("Saving extracted text to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"raw_text": raw_text},
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Get customer info

            customer = safe_request(
                request_type="GET",
                url=config.API_URL + f"/api/v1/customer/{customer_id}",
                data={}
            )
            output_language = customer.json().get("output_language", "English")
            logger.info(f"Customer output language: {output_language}")

            # -----------------------------------------------------------------------------------------------------------------------------
            # Run the smart summary prompt

            smart_summary = prompts["smart_summary"]
            data = run_ai_completition(ai_client=ai_client, prompt=smart_summary, document_text=raw_text, output_language=output_language)

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            logger.info("Saving smart summary to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={
                    "ai_category": data["top_category"],
                    "ai_sub_category": data["sub_category"],
                    "ai_summary_short": data["summary_short"],
                    "ai_summary_long": data["summary_long"]
                }
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Run the analysis criteria prompt
            analysis_criteria = prompts["analysis_criteria"]
            data = run_ai_completition(ai_client=ai_client, prompt=analysis_criteria, document_text=raw_text, output_language=output_language)

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            logger.info("Saving analysis criteria to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={
                    "ai_analysis_criteria": data["message"]
                }
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Run the features and insights prompt

            document = safe_request(
                        request_type="GET",
                        url=config.API_URL + f"/api/v1/document/get/{document_uuid}",
                        data={},
                    )
            ai_analysis_criteria = document.json()["ai_analysis_criteria"]


            features_and_insights = prompts["features_and_insights"]
            data = run_ai_completition(ai_client=ai_client, prompt=features_and_insights, document_extra=ai_analysis_criteria, output_language=output_language)
            features_and_insights_dict = json.loads(data["message"])

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            logger.info("Saving Analysis Features & Insights to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={
                    "ai_features_and_insights": json.dumps(features_and_insights_dict)
                }
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Map Eterny legacy document schemas - in English

            logger.info("Mapping existing Eterny.io Document Schemas")
            simple_prompt = prompts["map_existing_eterny.io_schemas"]

            with open("prompts/prompts.json", "r") as f:
                eterny_legacy_schema = f.read()

            raw_text += "\n\n schema:\n" + eterny_legacy_schema
            data = run_ai_completition(ai_client=ai_client, prompt=simple_prompt, document_text=raw_text, output_language="English")
            legacy_schema_dict = json.loads(data["message"])

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            logger.info("Update Eterny.io legacy schema to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"ai_enterny_legacy_schema": json.dumps(legacy_schema_dict)},
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # XXX TODO Mark off AI Alert

            random_alert = random.choice(["insights_available", "action_required", "reminder", "alert", ""])

            logger.info("Marking document as processed")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"ai_alert": random_alert},
            )
            logger.info("Analysis completed successfully")

            # -----------------------------------------------------------------------------------------------------------------------------
            # Record the tokens spent

            update_tokens_spent(
                document_uuid=document_uuid,
                add_tokens_spent=tokens_spent
            )

            # -----------------------------------------------------------------------------------------------------------------------------
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

        time.sleep(1)


if __name__ == "__main__":
    logger.info("Analysis worker started")
    main()
