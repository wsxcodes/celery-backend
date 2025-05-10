import logging

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend import config
from backend.api.api_v1.endpoints.customer_endpoints import (add_new_customer,
                                                             get_customer)
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

    customer = await get_customer(customer_id=session_id, db=db)
    logger.info("Customer data retrieved: %s", customer)

    logger.info("Rendering index page with session_id: %s", session_id)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "session_id": session_id,
            "customer": customer,
            "output_language": customer["output_language"]
        }
    )


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
