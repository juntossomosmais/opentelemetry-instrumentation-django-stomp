import json
import logging

from uuid import uuid4

from django.conf import settings
from django_stomp.builder import build_publisher
from opentelemetry import trace
from opentelemetry.semconv.trace import SpanAttributes

from opentelemetry_instrumentation_django_stomp import DjangoStompInstrumentor
from tests.support.helpers_tests import CustomFakeException
from tests.support.helpers_tests import get_latest_message_from_destination_using_test_listener
from tests.support.otel_helpers import TestBase
from tests.support.otel_helpers import get_traceparent_from_span


class PublisherInstrumentBase(TestBase):
    hook_callback = None
    test_queue_name = None
    correlation_id = None
    fake_payload_body = None
    publisher = None

    def setup_class(self):
        self.publisher_hook = self.hook_callback
        super().setup_class(self)

    def setup_method(self):
        # Arrange
        self.test_queue_name = f"/queue/test-publisher-queue-{uuid4()}"
        self.correlation_id = f"{uuid4()}"
        self.fake_payload_body = {"fake": "body"}
        self.publisher = build_publisher(f"test-publisher-{uuid4()}")

    def expected_span_attributes(self, mock_payload_size):
        return {
            SpanAttributes.MESSAGING_CONVERSATION_ID: self.correlation_id,
            SpanAttributes.MESSAGING_DESTINATION: self.test_queue_name,
            SpanAttributes.MESSAGING_MESSAGE_PAYLOAD_SIZE_BYTES: mock_payload_size,
            SpanAttributes.NET_PEER_NAME: settings.STOMP_SERVER_HOST,
            SpanAttributes.NET_PEER_PORT: settings.STOMP_SERVER_PORT,
            SpanAttributes.MESSAGING_SYSTEM: "rabbitmq",
        }


class TestPublisherInstrument(PublisherInstrumentBase):
    @staticmethod
    def hook_callback(span, body, headers):
        assert headers.get("traceparent", None) == get_traceparent_from_span(span)

    def test_should_match_traceparent_header_message_equals_to_traceparent_context_span(self, mock_payload_size):
        # Act
        self.publisher.send(
            queue=self.test_queue_name, body={"fake": "body"}, headers={"correlation-id": self.correlation_id}
        )

        # Assert
        # getting message without create a consumer span
        received_message = get_latest_message_from_destination_using_test_listener(self.test_queue_name)
        received_message_headers, received_message_body = received_message
        finished_spans = self.get_finished_spans()
        publisher_span = finished_spans.by_name("PUBLISHER")

        assert json.loads(received_message_body) == self.fake_payload_body
        assert received_message_headers.get("traceparent") == get_traceparent_from_span(publisher_span)
        assert dict(publisher_span.attributes) == self.expected_span_attributes(mock_payload_size)


class TestPublisherInstrumentHookRaises(PublisherInstrumentBase):
    @staticmethod
    def hook_callback(span, body, headers):
        assert headers.get("traceparent", None) == get_traceparent_from_span(span)
        raise CustomFakeException("fake exception")

    def test_should_log_exception_if_it_was_raised_inside_hook_function(self, mock_payload_size, caplog):
        # Arrange
        caplog.set_level(logging.WARNING)

        # Act
        self.publisher.send(
            queue=self.test_queue_name, body={"fake": "body"}, headers={"correlation-id": self.correlation_id}
        )

        # Assert
        # getting message without create a consumer span
        received_message = get_latest_message_from_destination_using_test_listener(self.test_queue_name)
        received_message_headers, received_message_body = received_message
        finished_spans = self.get_finished_spans()
        publisher_span = finished_spans.by_name("PUBLISHER")

        assert json.loads(received_message_body) == self.fake_payload_body
        assert received_message_headers.get("traceparent") == get_traceparent_from_span(publisher_span)
        assert dict(publisher_span.attributes) == self.expected_span_attributes(mock_payload_size)
        assert len(caplog.records) == 1
        assert caplog.records[0].message == "fake exception"


class TestPublisherInstrumentSupress(PublisherInstrumentBase):
    def setup_class(self):
        result = self.create_tracer_provider()
        self.tracer_provider, self.memory_exporter = result
        trace.set_tracer_provider(self.tracer_provider)
        setattr(settings, "OTEL_PYTHON_DJANGO_STOMP_INSTRUMENT", False)
        DjangoStompInstrumentor().instrument()

    def test_should_not_generate_span_if_suppress_key_is_in_context(self):
        # Act
        publisher = build_publisher(f"test-publisher-{uuid4()}")
        publisher.send(
            queue=self.test_queue_name, body={"fake": "body"}, headers={"correlation-id": self.correlation_id}
        )

        # Assert
        # getting message without create a consumer span
        received_message = get_latest_message_from_destination_using_test_listener(self.test_queue_name)
        received_message_headers, received_message_body = received_message
        finished_spans = self.get_finished_spans()
        assert len(finished_spans) == 0
        assert json.loads(received_message_body) == self.fake_payload_body
        assert received_message_headers.get("traceparent") is None
