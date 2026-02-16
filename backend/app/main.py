"""
Zavis LinkedIn Marketing Tool — FastAPI Application

A PhantomBuster-like platform for scraping LinkedIn company data and employees
from healthcare clinics and hospitals. Built on a Palantir ontology database.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "LinkedIn scraping and marketing automation tool for healthcare B2B. "
        "Connects to Google Sheets, resolves company LinkedIn URLs, scrapes "
        "employee data, and uses AI for role matching."
    ),
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
    }
