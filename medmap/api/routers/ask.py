from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def ask_data(body: dict = None):
    """Ask a question about the data."""
    return {"question": body.get("question", "") if body else "", "sql_generated": "", "results_as_dicts": None, "narrative_answer": None, "error": "Not implemented yet", "row_count": 0, "execution_time_ms": 0.0}


@router.get("/history")
async def get_ask_history():
    """Get ask-your-data query history."""
    return []
