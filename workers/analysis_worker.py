import datetime
import json
import logging
import random
import time

from backend import config
from backend.dependencies import ai_client
from backend.utils import prompt_generators
from backend.utils.helpers import safe_request
from backend.utils.prompt_generators import run_ai_completition

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

prompts = prompt_generators.load_prompts()


# XXX TODO retry policy on 3rd party API calls

# XXX TODO celery workers with backoff strategy

# XXX TODO record the tokens spent in the database and provide reporting endpoint

# XXX Record the tokens spent


def main():
    while True:
        logger.info("Querying pending documents for analysis")
        pending_document = safe_request(
            request_type="GET",
            url=config.API_URL + "/api/v1/artefact/list/pending?limit=1",
            data={},
        )
        if not pending_document:
            time.sleep(1)
            continue

        pending_documents = pending_document.json()

        if pending_documents:

            tokens_spent = 0

            document_uuid = pending_documents[0]["uuid"]
            output_language = pending_documents[0]["ai_output_language"]
            ai_analysis_mode = pending_documents[0]["ai_analysis_mode"]
            
            logger.info(f"Document to analyze: {document_uuid}")

            logger.info("Starting analysis")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={"analysis_status": "processing", "analysis_started_at": datetime.datetime.now().isoformat()},
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Extract text from the document
            logger.info("Extracting text from document")
            document_raw_text = safe_request(
                request_type="GET",
                url=config.API_URL + f"/api/v1/utils/extract_text_from_file?uuid={document_uuid}",
                data={},
            )
            document_raw_text = document_raw_text.json()

            # -----------------------------------------------------------------------------------------------------------------------------
            # Save the extracted text to the database
            logger.info("Saving extracted text to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={"document_raw_text": document_raw_text},
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Run the smart summary prompt
            logger.info("Running AI smart summary")
            smart_summary = prompts["smart_summary"]

            data = run_ai_completition(ai_client=ai_client, prompt=smart_summary, document_text=document_raw_text, output_language=output_language, inject_date=True)

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            ai_is_expired = False
            ai_expires = None
            document_expires_str = data["document_expires"]
            if document_expires_str:
                document_expires = datetime.datetime.fromisoformat(document_expires_str)
                ai_expires = document_expires.isoformat()
                ai_is_expired = data["is_expired"]

            logger.info("Saving smart summary to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={
                    "ai_category": data["top_category"],
                    "ai_sub_category": data["sub_category"],
                    "ai_summary_short": data["summary_short"],
                    "ai_summary_long": data["summary_long"],
                    "ai_expires": ai_expires,
                    "ai_is_expired": ai_is_expired
                }
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Run the analysis criteria prompt
            logger.info("Running AI analysis criteria")
            analysis_criteria = prompts["analysis_criteria"]
            data = run_ai_completition(ai_client=ai_client, prompt=analysis_criteria, document_text=document_raw_text, output_language=output_language)

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            logger.info("Saving analysis criteria to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={
                    "ai_analysis_criteria": data["message"]
                }
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Run the features and insights prompt
            logger.info("Running AI analysis features & insights")
            document = safe_request(
                        request_type="GET",
                        url=config.API_URL + f"/api/v1/artefact/{document_uuid}",
                        data={},
                    )
            ai_analysis_criteria = document.json()["ai_analysis_criteria"]

            features_and_insights = prompts["features_and_insights"]
            data = run_ai_completition(ai_client=ai_client, prompt=features_and_insights, document_extra1=ai_analysis_criteria, output_language=output_language, inject_date=True)
            features_and_insights_dict = data["features_and_insights"]

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            logger.info("Saving Analysis Features & Insights to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={
                    "ai_features_and_insights": json.dumps(features_and_insights_dict)
                }
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Run alerts and actions prompt
            logger.info("Running alerts and actions prompt")
            document = safe_request(
                        request_type="GET",
                        url=config.API_URL + f"/api/v1/artefact/{document_uuid}",
                        data={},
                    )

            document_extra2 = ""
            if ai_analysis_mode == "detailed":
                document_extra2 = "analysis_criteria = \"{ai_analysis_criteria}\"\nfeatures_and_insights = \"{ai_features_and_insights}\"\n\n"

            features_and_insights = prompts["alerts_and_actions"]
            data = run_ai_completition(
                ai_client=ai_client,
                prompt=features_and_insights,
                document_text=document_raw_text,
                document_extra1=str(datetime.datetime.now().date()),
                document_extra2=document_extra2,
                output_language=output_language
                )

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            ai_alerts_and_actions = data["alerts_and_actions"]

            logger.info("Saving Analysis Features & Insights to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={
                    "ai_alerts_and_actions": json.dumps(ai_alerts_and_actions)
                }
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Map Eterny legacy document schemas - in English
            logger.info("Mapping existing Eterny.io Document Schemas")
            simple_prompt = prompts["map_existing_eterny.io_schemas"]

            with open("prompts/prompts.json", "r") as f:
                eterny_legacy_schema = f.read()

            document_raw_text += "\n\n schema:\n" + eterny_legacy_schema
            data = run_ai_completition(ai_client=ai_client, prompt=simple_prompt, document_text=document_raw_text, output_language="English")
            legacy_schema_dict = json.loads(data["message"])

            usage = data.get("usage")
            tokens_spent += usage["total_tokens"]

            logger.info("Update Eterny.io legacy schema to database")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={"ai_eterny_legacy_schema": json.dumps(legacy_schema_dict)},
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Mark off AI Alert
            priority = ['alert', 'action_required', 'reminder', 'insights_available']

            # pick the highest‐priority alert present in the list
            document_ai_alert = next(
                (flag for flag in priority
                if any(item.get('findings_type') == flag for item in ai_alerts_and_actions)),
                None
            )

            # build your payload
            payload = {
                "ai_alerts_and_actions": json.dumps(ai_alerts_and_actions)
            }
            if document_ai_alert:
                payload["ai_alert"] = document_ai_alert

            logger.info("Marking document as processed")
            safe_request(
                request_type="PATCH",
                url=f"{config.API_URL}/api/v1/artefact/metadata/{document_uuid}",
                data=payload
            )
            logger.info("Analysis completed successfully")

            # -----------------------------------------------------------------------------------------------------------------------------
            # Execute the webhook
            logger.info("Executing the webhook")

            document = safe_request(
                request_type="GET",
                url=config.API_URL + f"/api/v1/artefact/{document_uuid}",
                data={},
            )

            webhook_url = pending_documents[0]["webhook_url"]
            logger.info(f"Webhook URL: {webhook_url}")
            safe_request(
                request_type="POST",
                url=webhook_url,
                data=json.dumps(document.json()),
                headers={"Content-Type": "application/json"},
            )

            # -----------------------------------------------------------------------------------------------------------------------------
            # Mark document as processed, update the cost
            logger.info("Marking document as processed")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/artefact/metadata/{document_uuid}",
                data={
                    "analysis_status": "processed",
                    "analysis_completed_at": datetime.datetime.now().isoformat()
                }
            )
            logger.info("Analysis completed successfully")

        else:
            logger.info("No pending documents found")

        time.sleep(1)


if __name__ == "__main__":
    logger.info("Analysis worker started")
    main()
