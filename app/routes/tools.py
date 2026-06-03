from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.pdf_tools import add_made_in_china_to_27up_pdf


router = APIRouter(prefix="/api/tools", tags=["public-tools"])


def _download_name(file_name: str) -> str:
    clean = re.sub(r"\.pdf$", "", file_name or "amazon-labels", flags=re.I)
    clean = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "-", clean).strip("-") or "amazon-labels"
    return f"{clean}-made-in-china.pdf"


@router.post("/made-in-china-pdf")
async def made_in_china_pdf(file: UploadFile = File(...), label_text: str = Form("Made in China")):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="请上传 PDF 文件。")
    text = (label_text or "Made in China").strip()[:80]
    if not text:
        text = "Made in China"
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="PDF 文件为空。")
    try:
        result = add_made_in_china_to_27up_pdf(content, text=text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"PDF 处理失败：{exc}") from exc
    filename = _download_name(file.filename or "amazon-labels.pdf")
    return Response(
        result,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
