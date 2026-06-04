from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="telemost-recorder gateway", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # TODO: routers/sessions.py — CRUD сессий, stop-recording, leave, transcribe, audio cleanup

    return app
