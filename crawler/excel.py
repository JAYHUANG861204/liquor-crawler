"""把爬到的資料輸出成 Excel（含商品縮圖）。"""
from __future__ import annotations

import io
import logging
from concurrent.futures import ThreadPoolExecutor

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .common import session

log = logging.getLogger("crawler")

HEAD = ["商品圖片", "網站", "品牌", "品名", "容量", "酒精濃度", "訂價", "促銷價", "幣別", "庫存", "商品連結"]
WIDTH = [12, 16, 20, 50, 10, 10, 11, 11, 7, 10, 14]
THUMB = 72  # 縮圖像素


def _thumb(url: str):
    try:
        from PIL import Image as PILImage
        r = session().get(url, timeout=20)
        r.raise_for_status()
        im = PILImage.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((THUMB, THUMB))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        buf.seek(0)
        return buf
    except Exception:  # noqa: BLE001
        return None


def write(products: list[dict], site_names: dict[str, str], path: str, images: bool = True, max_images: int = 1500) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "比價"
    hdr_fill = PatternFill("solid", fgColor="5A1424")
    thin = Side(style="thin", color="DDDDDD")
    for i, (h, w) in enumerate(zip(HEAD, WIDTH), start=1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = hdr_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 24

    thumbs = {}
    if images:
        urls = [p["image"] for p in products if p.get("image")][:max_images]
        with ThreadPoolExecutor(8) as ex:
            for u, t in zip(urls, ex.map(_thumb, urls)):
                if t:
                    thumbs[u] = t
        log.info("Excel 縮圖 %d / %d", len(thumbs), len(urls))

    from openpyxl.drawing.image import Image as XLImage
    for r, p in enumerate(products, start=2):
        vals = [
            None if p.get("image") in thumbs else ("看圖" if p.get("image") else None),
            site_names.get(p["site"], p["site"]), p.get("brand"), p.get("name"),
            f'{p["volume_ml"]:g} ml' if p.get("volume_ml") else None,
            f'{p["abv"]:g}%' if p.get("abv") is not None else None,
            p.get("list_price"), p.get("promo_price"), p.get("currency"), p.get("stock"),
            "開啟" if p.get("url") else None,
        ]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical="center", wrap_text=(c == 4))
            if c in (7, 8):
                cell.number_format = "#,##0.##"
        if p.get("image") and p["image"] not in thumbs:
            ws.cell(row=r, column=1).hyperlink = p["image"]
        if p.get("url"):
            ws.cell(row=r, column=11).hyperlink = p["url"]
            ws.cell(row=r, column=11).font = Font(color="0563C1", underline="single")
        if p.get("promo_price"):
            ws.cell(row=r, column=8).font = Font(bold=True, color="A86A00")
        if p.get("image") in thumbs:
            img = XLImage(thumbs[p["image"]])
            ws.add_image(img, f"A{r}")
            ws.row_dimensions[r].height = THUMB * 0.78
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEAD))}{max(2, len(products) + 1)}"
    wb.save(path)
