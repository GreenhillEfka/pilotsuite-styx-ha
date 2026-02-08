import os
import logging

from waitress import serve

from copilot_core.app import create_app


_LOGGER = logging.getLogger(__name__)


def main() -> None:
    app = create_app()
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8909"))

    # Helpful startup line: makes it obvious which port is used.
    try:
        cfg = app.config.get("COPILOT_CFG")
        ver = getattr(cfg, "version", "?")
    except Exception:  # noqa: BLE001
        ver = "?"

    _LOGGER.info("Copilot Core v%s listening on http://%s:%s", ver, host, port)

    serve(app, host=host, port=port)


if __name__ == "__main__":
    main()
