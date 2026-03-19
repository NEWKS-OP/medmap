from fastapi import APIRouter, UploadFile, File

router = APIRouter()


@router.post("")
async def upload_files(files: list[UploadFile] = File(...)):
    """Upload files for processing."""
    return [{"source_file": f.filename, "rows_total": 0, "rows_loaded": 0, "encoding_detected": "", "delimiter_detected": "", "warnings": []} for f in files]
