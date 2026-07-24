from .base import *  # noqa: F403


DEBUG = env_bool("DEBUG", default=True)  # noqa: F405

if not ALLOWED_HOSTS:  # noqa: F405
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
