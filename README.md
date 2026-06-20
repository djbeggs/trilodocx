# trilodocx
Simple API tool for extracting SAE tables from DOCX files and generating summary sentences.

## Quick start

Prerequisites: a Python 3.14+ environment and `uv` (optional) or `pip` available.

From the project root you can create a virtual environment and install dependencies with `uv` (recommended) or with pip:

Using `uv`:

```bash
make install
```

Or using `venv` + pip:

```bash
python -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/python -m pip install -e .
```

Run the development server:

```bash
make serve
# or
.venv/bin/uvicorn app.main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
```

API endpoint (simple):

- `POST /sae_summary` — accepts a single `.docx` file and two form fields `compound_a` and `compound_b`.

Example curl call:

```bash
curl -F "file=@client1_ae.docx" -F "compound_a=Placebo" -F "compound_b=Compound X" http://localhost:8000/sae_summary
```

## Tests & developer commands

Run tests:

```bash
make test
# or
.venv/bin/python -m pytest -q
```

Format and lint (uses `ruff`):

```bash
make format
make lint
```

Type checking:

```bash
make typecheck
```

Run full checks:

```bash
make check
```

## Assumptions about DOCX structure

This service focuses on extracting SAE (Serious Adverse Event) tables from DOCX files. The following assumptions guide detection and parsing:

- SAE table identification:
	- Table captions or nearby paragraphs contain the words `serious` or `SAE` (case-insensitive).
	- If a caption is not present, the service will still attempt to locate SAE tables by scanning table captions and nearby paragraphs.

- Table headers and columns:
	- A header row contains a column labeled `Preferred Term` (case-insensitive). This column holds the adverse event term names.
	- Columns for compounds can be labeled with compound names such as `Placebo`, `Compound X`, `CMP1`, `CMP2`, etc. The user provides two compound names when calling the API; the service matches those names (case-insensitive substring match) to header text to find the columns to compare.

- Totals row detection:
	- Totals rows are detected by phrases in the row text such as `Total number of participants with SAE`, `Number of participants with any SAE`, or rows that start with `Total` (case-insensitive).
	- Totals counts are extracted from the totals row by picking the integer that appears in the compound columns. If not found, the service returns `Totals not found in table.` in the response.

- Percentage parsing:
	- Percentages are expected to appear inside parentheses next to counts, e.g. `5 (12.5%)` or `(12.5%)`. The service extracts the numeric percentage inside parentheses and uses it unchanged — it does not recalculate percentages.

- Row parsing rules:
	- Rows following the header row are treated as preferred-term rows until the totals row is encountered (or the table ends).
	- If a preferred-term row contains no percentage for both selected compounds, the service emits `No participants experienced <term>.`
	- If both compounds have equal positive percentages, the service emits `An equal proportion of participants experienced <term> (<xx.%>).`
	- If one compound has 0% (or missing) and the other >0, the service emits `Only <xx.%> of participants who received <compound> experienced <term>.`
	- If both compounds >0, the service reports which compound had more participants with the term and includes both percentages.

## Notes and limitations

- The implementation uses heuristics and will not cover every DOCX layout. If your files use different header wording, table layouts, or percentage formats, please share a sample and I can adapt the parser.
- The service reads only one DOCX file per request.
- The project includes unit tests in `tests/` that cover several edge cases and examples.


