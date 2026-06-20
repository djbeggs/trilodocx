import re
import io
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from docx import Document
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph
from docx.oxml.text.paragraph import CT_P

app = FastAPI(title="TriloDocx SAE", description="SAE table extractor and summarizer")


class TableSummary(BaseModel):
    title: str
    table_number: int
    totals_sentence: str
    sentences: List[str]


class SAEResponse(BaseModel):
    selected_compounds: List[str]
    tables: List[TableSummary]


def _is_caption_paragraph(paragraph: Paragraph) -> bool:
    text = paragraph.text.strip()
    if not text:
        return False
    style_name = getattr(paragraph.style, "name", "")
    if style_name and "caption" in style_name.lower():
        return True
    return text.lower().startswith("table") or len(text) < 200


def _get_table_name(table: DocxTable, doc: Document) -> Optional[str]:  # type: ignore
    body_children = list(doc.element.body.iterchildren())  # type: ignore
    for idx, child in enumerate(body_children):
        if child is table._tbl:
            # check previous and next for caption paragraphs
            for candidate in (
                body_children[idx - 1] if idx > 0 else None,
                body_children[idx + 1] if idx + 1 < len(body_children) else None,
            ):
                if isinstance(candidate, CT_P):
                    para = Paragraph(candidate, doc)
                    if _is_caption_paragraph(para):
                        return para.text.strip()
            break
    return None


def _is_sae_title(title: str) -> bool:
    return bool(re.search(r"\b(?:serious|sae)\b", title, flags=re.I))
    # TODO: remove regex to improve readability in future.


def _find_header_row(table: DocxTable) -> Optional[int]:
    for idx, row in enumerate(table.rows):
        cells = [c.text.strip().lower() for c in row.cells]
        if any("preferred term" in c for c in cells):
            return idx
    return None


def _extract_percent(cell_text: str) -> Optional[float]:
    m = re.search(r"\((\d+(?:\.\d+)?)%\)", cell_text)
    # TODO: remove regex to improve readability in future.
    if m:
        return float(m.group(1))
    return None


def _extract_count(cell_text: str) -> Optional[int]:
    m = re.search(r"(\d+)\s*(?:\(|$)", cell_text)
    # TODO: remove regex to improve readability in future.
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


@app.get("/health")
async def health():
    return {"status": "ok"}
    # TODO: Fix health status before production deployment. Currently, it always returns "ok" even if the app is not healthy.


@app.post("/sae-summary", response_model=SAEResponse)
async def sae_summary(
    file: UploadFile = File(...),
    compound_a: str = Form(...),
    compound_b: str = Form(...),
):
    """Endpoint for processing and summerising SAE tables inside a docx file

    Args:
        file (UploadFile, optional): Docx file containing tables to summarise. Defaults to File(...).
        compound_a (str, optional): Name of the first compound. Defaults to Form(...).
        compound_b (str, optional): Name of the second compound. Defaults to Form(...).

    Raises:
        HTTPException: If the file is not docx
        HTTPException: If compounds are missing
        HTTPException: If no SAE tables are found
        HTTPException: If any uncaught exceptions occur

    Returns:
        _type_: summary of SAE tables found in the docx file, including selected compounds and table details.
    """

    if not file.filename.lower().endswith(".docx"):  # type: ignore
        raise HTTPException(status_code=400, detail="file must be a .docx")

    if not compound_a or not compound_b:
        raise HTTPException(status_code=400, detail="two compounds required")

    try:
        data = await file.read()
        doc = Document(io.BytesIO(data))

        sae_tables = []
        # scan tables and their names
        for idx, table in enumerate(doc.tables, start=1):
            title = _get_table_name(table, doc) or f"Table {idx}"
            if _is_sae_title(title):
                sae_tables.append((idx, table, title))

        if not sae_tables:
            raise HTTPException(status_code=400, detail="No SAE table found")

        results = []
        for table_number, table, title in sae_tables:
            header_idx = _find_header_row(table)
            if header_idx is None:
                continue

            headers = [c.text.strip() for c in table.rows[header_idx].cells]
            # find columns for preferred term and the two compounds, supports tables with columns that are neither of the used compounds.
            pref_idx = None
            col_a = col_b = None
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if "preferred term" in header_lower:
                    pref_idx = i
                if compound_a.lower() in header_lower:
                    col_a = i
                    compound_a = header.strip()  # use the actual header text for the compound name
                if compound_b.lower() in header_lower:
                    col_b = i
                    compound_b = header.strip()  # use the actual header text for the compound name

            if pref_idx is None or col_a is None or col_b is None:
                # skip tables that don't include both compounds
                continue

            # parse rows after header until totals row
            sentences = []
            totals_counts: dict[str, int | None] = {"a": None, "b": None}

            for row in table.rows[header_idx + 1 :]:
                cells = [c.text.strip() for c in row.cells]
                # detect totals row by phrase
                row_text = " ".join(cells).lower()
                if (
                    "total number" in row_text
                    or "number of participants with any sae" in row_text
                    or "total number of participants with sae" in row_text
                    or row_text.startswith("total")
                ):
                    # extract counts for compounds
                    if col_a < len(cells):
                        totals_counts["a"] = _extract_count(cells[col_a])
                    if col_b < len(cells):
                        totals_counts["b"] = _extract_count(cells[col_b])
                    continue

                # regular preferred term rows
                if pref_idx < len(cells):
                    term = cells[pref_idx]
                    val_a = cells[col_a] if col_a < len(cells) else ""
                    val_b = cells[col_b] if col_b < len(cells) else ""

                    pct_a = _extract_percent(val_a)
                    pct_b = _extract_percent(val_b)
                    # TODO: calculated pct if missing, but count present, or vice versa. Currently, if either is missing, it will be treated as zero. OUT OF SCOPE FOR NOW.

                    # rule: both zero or missing
                    if (pct_a is None or pct_a == 0) and (pct_b is None or pct_b == 0):
                        sentences.append(f"No participants experienced {term}.")
                        continue

                    # rule: both present and >0
                    if pct_a and pct_b and pct_a > 0 and pct_b > 0:
                        if abs(pct_a - pct_b) < 1e-6:
                            sentences.append(
                                f"An equal proportion of participants experienced {term} ({pct_a}%)."
                            )
                        elif pct_a > pct_b:
                            sentences.append(
                                f"More participants who received {compound_a} ({pct_a}%) experienced {term} compared to {compound_b} ({pct_b}%)."
                            )
                        else:
                            sentences.append(
                                f"More participants who received {compound_b} ({pct_b}%) experienced {term} compared to {compound_a} ({pct_a}%)."
                            )
                        continue

                    # rule: one is zero (or missing) and the other >0
                    if (pct_a is None or pct_a == 0) and pct_b and pct_b > 0:
                        sentences.append(
                            f"Only {pct_b}% of participants who received {compound_b} experienced {term}."
                        )
                        continue

                    if (pct_b is None or pct_b == 0) and pct_a and pct_a > 0:
                        sentences.append(
                            f"Only {pct_a}% of participants who received {compound_a} experienced {term}."
                        )
                        continue

            # build totals sentence
            if totals_counts["a"] is None or totals_counts["b"] is None:
                totals_sentence = "Totals not found in table."
            else:
                totals_sentence = f"A total of {totals_counts['a']} participants received {compound_a}, and a total of {totals_counts['b']} participants received {compound_b}."

            results.append(
                TableSummary(
                    title=title,
                    table_number=table_number,
                    totals_sentence=totals_sentence,
                    sentences=sentences,
                )
            )

        if not results:
            raise HTTPException(
                status_code=400, detail="No SAE table containing both compounds found"
            )

        return SAEResponse(selected_compounds=[compound_a, compound_b], tables=results)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    # simple local server for testing; in production use a proper ASGI server like gunicorn or uvicorn with workers
    uvicorn.run(app, host="0.0.0.0", port=8000)
