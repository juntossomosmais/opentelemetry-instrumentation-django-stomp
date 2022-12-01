from unittest import mock

import pytest

from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind

from opentelemetry_instrumentation_django_stomp.utils.span import get_span


class TestSpan:
    @pytest.mark.parametrize(
        "test_params",
        [
            {
                "fake_broker_host": "fake_host",
                "fake_broker_port": "fake_port",
                "fake_broker_system": "fake_system",
                "operation": "fake_operation",
                "destination": "fake_destination",
                "headers": {"correlation-id": "fake_value"},
                "body": {"fake_key": "fake_value"},
                "span_kind": SpanKind.INTERNAL,
                "span_name": "fake_span_name",
            },
            {
                "fake_broker_host": "fake_host",
                "fake_broker_port": "fake_port",
                "operation": "fake_operation",
                "destination": "fake_destination",
                "headers": {"correlation-id": "fake_value"},
                "body": {"fake_key": "fake_value"},
                "span_kind": SpanKind.INTERNAL,
                "span_name": "fake_span_name",
            },
            {
                "fake_broker_host": "fake_host",
                "fake_broker_port": "fake_port",
                "fake_broker_system": None,
                "operation": "fake_operation",
                "destination": "fake_destination",
                "headers": {"correlation-id": "fake_value"},
                "body": {"fake_key": "fake_value"},
                "span_kind": SpanKind.CONSUMER,
                "span_name": "fake_span_name",
            },
        ],
    )
    def test_should_enrich_span_with_host_data_based_in_env_configurations_and_parameters(
        self, test_params, settings, mock_payload_size
    ):
        # Arrange
        fake_broker_host = test_params["fake_broker_host"]
        fake_broker_port = test_params["fake_broker_port"]
        fake_broker_system = test_params.get("fake_broker_system", False)

        settings.STOMP_SERVER_HOST = fake_broker_host
        settings.STOMP_SERVER_PORT = fake_broker_port
        if fake_broker_system:
            settings.STOMP_SYSTEM = fake_broker_system

        expected_span_attributes_host = {
            SpanAttributes.NET_PEER_NAME: fake_broker_host,
            SpanAttributes.NET_PEER_PORT: fake_broker_port,
            SpanAttributes.MESSAGING_SYSTEM: fake_broker_system or "rabbitmq",
        }

        expected_span_attributes_message = {
            SpanAttributes.MESSAGING_DESTINATION: test_params["destination"],
            SpanAttributes.MESSAGING_OPERATION: test_params["operation"],
            SpanAttributes.MESSAGING_CONVERSATION_ID: test_params["headers"].get("correlation-id"),
            SpanAttributes.MESSAGING_MESSAGE_PAYLOAD_SIZE_BYTES: mock_payload_size,
        }
        mocked_span = mock.MagicMock()

        mocked_tracer = mock.MagicMock()
        mocked_tracer.start_span.return_value = mocked_span

        # Act
        get_span(
            tracer=mocked_tracer,
            operation=test_params["operation"],
            destination=test_params["destination"],
            headers=test_params["headers"],
            body=test_params["body"],
            span_name=test_params["span_name"],
            span_kind=test_params["span_kind"],
        )

        # Assert
        assert mocked_span.is_recording.call_count == 1
        mocked_span.set_attributes.assert_any_call(expected_span_attributes_host)
        mocked_span.set_attributes.assert_any_call(expected_span_attributes_message)
