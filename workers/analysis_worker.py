import logging
import time

from backend import config
from backend.utils.helpers import perform_request

logging.basicConfig(level=logging.INFO)
import time

from backend import config
from backend.utils.helpers import perform_request

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


# XXX call endpoint to generate preview


def main():
    while True:
        logger.info("Querying pending documents for analysis")
        pending_document = perform_request(
            request_type="GET",
            url=config.API_URL + "/api/v1/document/list/pending?limit=1",
            data={},
        )
        if pending_document.status_code == 200:
            document = pending_document.json()
            logger.info(f"Document to analyze: {document}")
        else:
            logger.info("No pending documents found")
        time.sleep(2)


if __name__ == "__main__":
    logger.info("Analysis worker started")
    main()
