"""Run: python -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload"""

if __name__ == "__main__":
    import uvicorn

    from app.config import settings

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
