from .base import *  # noqa: F403,F401

import dj_database_url

DEBUG = True

DATABASES = {
    "default": dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=False,
    )
}

