import logging.config

from flask import Flask

app = Flask(__name__)
app.config.from_envvar('SETTINGS')


def _setup_logger():
    # Initialize logger once before configuring.
    _ = app.logger
    logging.config.dictConfig({
        "version": 1,
        "formatters": {
            "brief": {
                "format": "[%(asctime)s][%(levelname)s] %(message)s",
                "datefmt": "%H:%M:%S"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "brief",
                "level": "INFO",
                "stream": "ext://sys.stdout"
            },
        },
        "loggers": {
            app.logger_name: {
                "level": "DEBUG" if app.config.get("DEBUG_LOGGING") else "INFO",
                "handlers": ["console"]
            }
        }
    })


_setup_logger()

import leaguebot.leaguebot
