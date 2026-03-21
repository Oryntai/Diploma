from fastapi import FastAPI


app = FastAPI(title="IoT Security Monitoring Backend")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "backend",
    }
