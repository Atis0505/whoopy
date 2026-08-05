"""Run: python run.py  |  prod: uvicorn app.main:app --host 0.0.0.0 --port 8090 --workers 2"""

if __name__ == "__main__":
    import uvicorn

    from app.config import settings

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=not settings.is_production,
    )
