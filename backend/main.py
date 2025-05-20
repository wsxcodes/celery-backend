import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend import config
from backend.api.api_v1.routers import api_router
from backend.dependencies import init_db

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

templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
