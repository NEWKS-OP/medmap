"""
Upload router — file upload endpoint.
POST /api/upload
"""

import os
import tempfile
import logging

from fastapi import APIRouter, UploadFile, File

logger = logging.getLogger(__name__)

router = APIRouter(responses={200: {"description": "Upload results"}})


@router.post("")
async def upload_files(files: list[UploadFile] = File(..., description="Files to upload for pipeline processing")):
    """Upload files for processing through the data ingestion pipeline.

    Accepts CSV, XLSX, and PDF files."""
    from pipeline.ingestion import DataIngester

    ingester = DataIngester()
    results = []
    logger.info("Received %d files for upload", len(files))

    for upload in files:
        try:
            suffix = os.path.splitext(upload.filename or "file")[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await upload.read()
                tmp.write(content)
                tmp_path = tmp.name

            try:
                logger.info("Processing uploaded file: %s", upload.filename)
                df, result = ingester.load(tmp_path, original_filename=upload.filename)
                results.append({
                    "source_file": upload.filename,
                    "rows_total": result.rows_total,
                    "rows_loaded": result.rows_loaded,
                    "encoding_detected": result.encoding_detected,
                    "delimiter_detected": result.delimiter_detected,
                    "warnings": result.warnings,
                })
            finally:
                os.unlink(tmp_path)

        except Exception as e:
            logger.error("Upload failed for %s: %s", upload.filename, e)
            results.append({
                "source_file": upload.filename,
                "rows_total": 0,
                "rows_loaded": 0,
                "encoding_detected": "",
                "delimiter_detected": "",
                "warnings": [f"Upload error: {e}"],
            })

    return results
