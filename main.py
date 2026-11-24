"""FastAPI server for the Himachal Pradesh travel planner.

Run with:  uvicorn main:app --reload
"""
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from data import build_itinerary

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

app = FastAPI(title="Himachal Pradesh Travel Mission Command Centre")


def read_template(name: str) -> str:
    """Read a fixed template file as UTF-8 (no Jinja2, so no template-cache issues)."""
    path = os.path.join(TEMPLATE_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        raise HTTPException(status_code=500, detail=f"Template {name} not found")


# The page is served as-is, so any ?season=...&trails=... query string stays in the
# browser's URL and is read by the page's own script (and by the API below).
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/index.html", response_class=HTMLResponse, include_in_schema=False)
def index_page():
    return HTMLResponse(read_template("index.html"))


@app.get("/details", response_class=HTMLResponse, include_in_schema=False)
@app.get("/details.html", response_class=HTMLResponse, include_in_schema=False)
def details_page():
    return HTMLResponse(read_template("details.html"))


@app.get("/api/itinerary-data")
def itinerary_data(
    season: str = Query("Summer", max_length=20),
    trails: str = Query("", max_length=600, description="Comma-separated trails and custom places"),
    travellers: int = Query(2, ge=1, le=20),
    tier: str = Query("Comfort", max_length=20),
    days: int | None = Query(None, ge=1, le=40),
):
    """Budget estimates, risk profile and safety notes for the chosen season and places."""
    return build_itinerary(season=season, trails=trails, travellers=travellers, tier=tier, days=days)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
