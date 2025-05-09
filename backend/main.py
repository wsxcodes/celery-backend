import logging
from datetime import datetime

import humanize
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend import config
from backend.api.api_v1.endpoints.customer_endpoints import (
    add_new_customer, get_customer, list_customer_documents)
from backend.api.api_v1.routers import api_router
from backend.decorators import log_endpoint
from backend.dependencies import get_db, init_db

API_V1_STR = "/api/v1"

# Ensure logging is properly configured
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Set up logging for the kernel
logging.getLogger("kernel").setLevel(logging.DEBUG)

app = FastAPI(
    title="EternyIQ API",
    openapi_url=f"{API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redocs"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add the Session Middleware
app.add_middleware(
    SessionMiddleware, secret_key=config.SECRET_KEY, max_age=3600  # 1 hour
)

# Include routers
app.include_router(api_router, prefix=API_V1_STR)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_home(request: Request, db=Depends(get_db)):
    logger = logging.getLogger(__name__)

    session_id = request.session.get("session_id")
    if session_id:
        logger.info("Existing session_id found: %s", session_id)
    else:
        logger.info("No session_id found, generating a new one.")

    # If no session ID exists, generate a new one
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id
        logger.info("** Generated new session_id: %s", session_id)
        await add_new_customer(customer_id=session_id, output_language="Czech", db=db)

    files = await list_customer_documents(session_id, db)
    categorized_documents = files["categorized_documents"]
    logger.info("Found %d categories", len(categorized_documents))

    for cat_index, cat in enumerate(categorized_documents):
        logger.info("Category %d: %s", cat_index + 1, cat.get("category", "Unknown"))
        for doc_index, doc in enumerate(cat.get("documents", [])):
            logger.info("Doc %d in category %d keys: %s", doc_index + 1, cat_index + 1, list(doc.keys()))

            # Log raw file_size before humanizing
            if "file_size" in doc:
                logger.info("Raw file size for doc %d in category %d: %s", doc_index + 1, cat_index + 1, doc["file_size"])
                doc["file_size_human"] = humanize.naturalsize(doc["file_size"], binary=False)
                logger.info("Humanized file size for doc %d in category %d: %s", doc_index + 1, cat_index + 1, doc["file_size_human"])

            # Check the raw uploaded_at before humanizing
            if "uploaded_at" in doc:
                logger.info("Raw uploaded_at for doc %d in category %d: %s", doc_index + 1, cat_index + 1, doc["uploaded_at"])

                # Convert the uploaded_at string to datetime
                try:
                    uploaded_at = datetime.fromisoformat(doc["uploaded_at"])
                    logger.info("Converted uploaded_at to datetime for doc %d in category %d", doc_index + 1, cat_index + 1)
                    doc["uploaded_at_human"] = humanize.naturaltime(datetime.now() - uploaded_at)
                    logger.info("Humanized uploaded_at for doc %d in category %d: %s", doc_index + 1, cat_index + 1, doc["uploaded_at_human"])
                except ValueError:
                    logger.warning("uploaded_at for doc %d in category %d is not in the correct datetime format: %s", doc_index + 1, cat_index + 1, doc["uploaded_at"])

    customer = await get_customer(customer_id=session_id, db=db)
    logger.info("Customer data retrieved: %s", customer)

    logger.info("Rendering index page with session_id: %s", session_id)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "session_id": session_id,
            "customer": customer,
            "categorized_documents": categorized_documents,
            "output_language": customer["output_language"]
        }
    )

# XXX TEMP devel
@app.get("/devel-document", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_categories(request: Request, db=Depends(get_db)):
    return templates.TemplateResponse("document-1.html", {"request": request})


@app.get("/categories", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_categories(request: Request, db=Depends(get_db)):
    return templates.TemplateResponse("categories.html", {"request": request})


@app.get("/reset", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def reset_customer(request: Request, db=Depends(get_db)):
    import uuid
    session_id = str(uuid.uuid4())
    request.session["session_id"] = session_id
    logger.info("** Generated new session_id: %s", session_id)
    await add_new_customer(customer_id=session_id, output_language="Czech", db=db)
    return RedirectResponse(url="/", status_code=302)


@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
@log_endpoint
async def read_document(request: Request, full_path: str):
    filename = "example.txt"
    logger.info("Rendering document page for path: %s", full_path)
    return templates.TemplateResponse("document.html", {"request": request, "filename": filename})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
