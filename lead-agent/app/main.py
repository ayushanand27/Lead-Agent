"""FastAPI app and webhook routes — implemented in step 5."""

from fastapi import FastAPI

app = FastAPI(title="WhatsApp Lead Management Agent")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
