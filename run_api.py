"""Run the local Flask API."""


def main() -> None:
    from app.api.factory import create_app
    from app.config.settings import get_settings

    settings = get_settings()
    app = create_app(settings)
    app.run(host=settings.flask_host, port=settings.flask_port, debug=settings.flask_debug)


if __name__ == "__main__":
    main()