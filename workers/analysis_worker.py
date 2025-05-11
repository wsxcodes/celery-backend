import datetime
import logging
import time

from backend import config
from backend.utils.helpers import safe_request

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


# extract entities, e.g. people, organizations, locations, full names, etc.

# category

# Smart Summaries
# TL;DR of each document in human-readable form. Highlight key obligations, penalties, rights, and deadlines.

# # Analysis Features
# Expiry/Deadline Management
# Detect contract end dates, renewal clauses, trial periods. Send reminders for expiration, automatic renewals, cancellation windows. Sync with Google/Outlook/iCal.

# Compliance Alerts
# Identify missing signatures, outdated IDs, unfulfilled clauses. GDPR/CCPA compliance checks for stored documents.

# Smart Categorization
# Auto-tagging by document type: wills, insurance, leases, employment, etc. Separate personal vs business assets.

# Risk Analysis
# Highlight risky clauses (e.g., high penalties, non-compete traps, vague language). Compare clauses to industry norms.

# Beneficiary & Heir Auditing
# Check if wills, accounts, policies list outdated or missing beneficiaries. Ensure all heirs are accounted for.

# Contract Comparison
# Compare new contracts to older ones to identify changes and stricter terms.

# Action Suggestions
# Receive proactive suggestions like reviewing expiring insurance or updating outdated medical proxies.

# Succession Planning AI
# Create a digital vault for heirs with essential document summaries for family or legal counsel.

# Timeline & Audit Trails
# Track the evolution of key documents, such as trust updates or revised contracts, with version history.

# Document Health Score
# Rate completeness, legal soundness, and currency of important files.


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

            # XXX TEMP delay for testing
            time.sleep(5)

            # XXX TODO Mark off AI Alert
            logger.info("Marking document as processed")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"ai_alert": "insights_available"},
            )
            logger.info("Analysis completed successfully")

            # XXX TODO do the category as the very last step

            # Mark document as processed
            logger.info("Marking document as processed")
            safe_request(
                request_type="PATCH",
                url=config.API_URL + f"/api/v1/document/metadata/{document_uuid}",
                data={"analysis_status": "processed", "analysis_completed_at": datetime.datetime.now().isoformat(), "analysis_cost": tokens_spent},
            )
            logger.info("Analysis completed successfully")

        else:
            logger.info("No pending documents found")

        time.sleep(0.5)


if __name__ == "__main__":
    logger.info("Analysis worker started")
    main()
