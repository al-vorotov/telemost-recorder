import uvicorn

from shared.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "services.gateway.app:create_app",
        factory=True,
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
