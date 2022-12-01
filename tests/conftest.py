import os
import uuid

import pytest

from django.conf import settings


@pytest.fixture
def mock_payload_size(mocker):
    """Mock function to get size in bytes of payload queue"""
    get_sizeof_value = 1
    mocker.patch("sys.getsizeof").return_value = get_sizeof_value
    return get_sizeof_value


def pytest_configure():
    settings.configure(
        INSTALLED_APPS=["opentelemetry_instrumentation_django_stomp", "django_stomp"],
        STOMP_SERVER_HOST=os.getenv("STOMP_SERVER_HOST"),
        STOMP_SERVER_PORT=os.getenv("STOMP_SERVER_PORT"),
        STOMP_SERVER_STANDBY_HOST=os.getenv("STOMP_SERVER_STANDBY_HOST"),
        STOMP_SERVER_STANDBY_PORT=os.getenv("STOMP_SERVER_STANDBY_PORT"),
        STOMP_SERVER_USER=os.getenv("STOMP_SERVER_USER"),
        STOMP_SERVER_PASSWORD=os.getenv("STOMP_SERVER_PASSWORD"),
        STOMP_USE_SSL=os.getenv("STOMP_USE_SSL"),
        STOMP_LISTENER_CLIENT_ID=os.getenv("STOMP_LISTENER_CLIENT_ID"),
        STOMP_CORRELATION_ID_REQUIRED=os.getenv("STOMP_CORRELATION_ID_REQUIRED"),
        STOMP_PROCESS_MSG_ON_BACKGROUND=os.getenv("STOMP_PROCESS_MSG_ON_BACKGROUND"),
        STOMP_OUTGOING_HEARTBEAT=os.getenv("STOMP_OUTGOING_HEARTBEAT"),
        STOMP_INCOMING_HEARTBEAT=os.getenv("STOMP_INCOMING_HEARTBEAT"),
        DATABASES={
            "default": {
                "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
                "NAME": os.getenv("DB_DATABASE", f"test_db-{uuid.uuid4()}"),
                "USER": os.getenv("DB_USER"),
                "HOST": os.getenv("DB_HOST"),
                "PORT": os.getenv("DB_PORT"),
                "PASSWORD": os.getenv("DB_PASSWORD"),
                "TEST": {"NAME": os.getenv("DB_DATABASE", f"test_db-{uuid.uuid4()}")},
            }
        },
    )
