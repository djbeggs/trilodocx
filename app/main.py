from fastapi import FastAPI, UploadFile, File, Form, HTTPException

app = FastAPI(title="TriloDocx Simple SAE")

@app.get("/health")
async def health():
	return {"status": "ok"}

@app.post("/sae_summary")
async def sae_summary(
	file: UploadFile = File(...), compound_a: str = Form(...), compound_b: str = Form(...)
):
    """Endpoint for processing and summerising SAE tables inside a docx file

    Args:
        file (File, optional): Docx file containing tables to summerise. Defaults to File(...).
        compound_a (str, optional): Name of the first compound. Defaults to Form(...).
        compound_b (str, optional): Name of the second compound. Defaults to Form(...).

    Raises:
        HTTPException: If the file is not a .docx or if either compound name is missing, raises a 400 HTTPException.

    Returns:
        _type_: summary of SAE tables found in the docx file, including selected compounds and table details.
    """
	
	if not file.filename.lower().endswith(".docx"): # type: ignore
		raise HTTPException(status_code=400, detail="file must be a .docx")

	if not compound_a:
		raise HTTPException(status_code=400, detail="compound_a is required")

	if not compound_b:
		raise HTTPException(status_code=400, detail="compound_b is required")

	return {"filename": file.filename, "compound_a": compound_a, "compound_b": compound_b}

if __name__ == "__main__":
    import uvicorn
    # simple local server for testing; in production use a proper ASGI server like gunicorn or uvicorn with workers
    uvicorn.run(app, host="0.0.0.0", port=8000) 
