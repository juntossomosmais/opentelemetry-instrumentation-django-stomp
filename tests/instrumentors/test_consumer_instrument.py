import json
import logging

from uuid import uuid4

from django.conf import settings
from django_stomp.builder import build_listener
from django_stomp.builder import build_publisher
from django_stomp.execution import start_processing
from django_stomp.services.consumer import StompFrame
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_DESTINATION_NAME
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_MESSAGE_BODY_SIZE
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_MESSAGE_CONVERSATION_ID
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_OPERATION_TYPE
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_SYSTEM
from opentelemetry.semconv._incubating.attributes.net_attributes import NET_PEER_NAME
from opentelemetry.semconv._incubating.attributes.net_attributes import NET_PEER_PORT
from opentelemetry.semconv.trace import MessagingOperationValues

from tests.support.helpers_tests import CustomFakeException
from tests.support.helpers_tests import get_latest_message_from_destination_using_test_listener
from tests.support.otel_helpers import TestBase


def callback_ack(payload):
    payload.ack()


def callback_nack(payload):
    payload.nack()


class TestConsumerBase(TestBase):
    hook_callback = None
    consumer_id = None
    queue_consumer_name = None
    correlation_id = None
    fake_payload_body = None
    fake_payload_headers = None
    span_host_attributes = None
    listener = None
    fake_frame = None

    def setup_class(self):
        self.consumer_hook = self.hook_callback
        super().setup_class(self)

    def setup_method(self):
        # Arrange
        self.consumer_id = f"some-destination-{uuid4()}"
        self.queue_consumer_name = f"/queue/test-publisher-queue-{uuid4()}"
        self.correlation_id = f"{uuid4()}"
        self.fake_payload_body = {"fake": "body"}
        self.fake_payload_headers = {
            "tshoot-destination": self.queue_consumer_name,
            "correlation-id": self.correlation_id,
            "message-id": str(uuid4()),
        }
        self.span_host_attributes = {
            NET_PEER_NAME: settings.STOMP_SERVER_HOST,
            NET_PEER_PORT: settings.STOMP_SERVER_PORT,
            MESSAGING_SYSTEM: "rabbitmq",
        }
        self.listener = build_listener(self.consumer_id, should_process_msg_on_background=True)
        self.fake_frame = StompFrame(
            cmd="FAKE_CMD", headers=self.fake_payload_headers, body=json.dumps(self.fake_payload_body)
        )

    def expected_span_attributes(self, mock_payload_size):
        return {
            MESSAGING_DESTINATION_NAME: self.queue_consumer_name,
            MESSAGING_OPERATION_TYPE: str(MessagingOperationValues.RECEIVE.value),
            MESSAGING_MESSAGE_CONVERSATION_ID: self.correlation_id,
            MESSAGING_MESSAGE_BODY_SIZE: mock_payload_size,
            **self.span_host_attributes,
        }


class TestConsumerInstrument(TestConsumerBase):
    @staticmethod
    def hook_callback(span, body, headers):
        assert span.name == f"process {headers.get('tshoot-destination')}"

    def test_should_create_child_span_consumer_when_traceparent_header_exists_in_on_message_payload(
        self, mock_payload_size, mocker
    ):
        # Arrange
        publisher = build_publisher(f"test-publisher-{uuid4()}")
        publisher.send(queue=self.queue_consumer_name, body=self.fake_payload_body, headers=self.fake_payload_headers)

        received_message = get_latest_message_from_destination_using_test_listener(self.queue_consumer_name)
        received_message_headers, received_message_body = received_message

        mocker.patch("django_stomp.services.consumer.connect.StompConnection11.send_frame")
        fake_frame_with_trace_parent_header = StompFrame(
            cmd="FAKE_CMD", headers=received_message_headers, body=json.dumps(received_message_body)
        )

        common_span_attributes = {
            MESSAGING_DESTINATION_NAME: self.queue_consumer_name,
            MESSAGING_MESSAGE_CONVERSATION_ID: self.correlation_id,
            MESSAGING_MESSAGE_BODY_SIZE: mock_payload_size,
            **self.span_host_attributes,
        }

        expected_consumer_span_attributes = {
            MESSAGING_OPERATION_TYPE: str(MessagingOperationValues.RECEIVE.value),
            **common_span_attributes,
        }

        expected_publisher_span_attributes = {
            MESSAGING_OPERATION_TYPE: str(MessagingOperationValues.PUBLISH.value),
            **common_span_attributes,
        }

        # Act
        self.listener.on_message(fake_frame_with_trace_parent_header)
        self.listener.shutdown_worker_pool()

        # Assert
        finished_spans = self.get_finished_spans()
        finished_consumer_span = finished_spans.by_name(f"process {self.queue_consumer_name}")
        finished_publisher_span = finished_spans.by_name(f"send {self.queue_consumer_name}")

        assert dict(finished_consumer_span.attributes) == expected_consumer_span_attributes
        assert dict(finished_publisher_span.attributes) == expected_publisher_span_attributes
        # finished_consumer_span is a child of finished_publisher_span
        assert finished_consumer_span.parent.span_id == finished_publisher_span.context.span_id
        assert finished_consumer_span.parent.trace_id == finished_publisher_span.context.trace_id
        assert json.loads(received_message_body) == self.fake_payload_body

    def test_should_create_consumer_span_in_on_message_function(self, mock_payload_size, mocker):
        # Arrange
        mocker.patch("django_stomp.services.consumer.connect.StompConnection11.send_frame")

        # Act
        self.listener.on_message(self.fake_frame)
        self.listener.shutdown_worker_pool()

        # Assert
        finished_consumer_span = self.get_finished_spans().by_name(f"process {self.queue_consumer_name}")
        assert dict(finished_consumer_span.attributes) == self.expected_span_attributes(mock_payload_size)

    def test_should_create_ack_span_on_ack_listener_action(self, mocker):
        # Arrange
        publisher = build_publisher(f"test-publisher-{uuid4()}")
        publisher.send(queue=self.queue_consumer_name, body=self.fake_payload_body, headers=self.fake_payload_headers)

        # Act
        start_processing(
            self.queue_consumer_name,
            "tests.instrumentors.test_consumer_instrument.callback_ack",
            is_testing=True,
        )

        # Assert
        ack_finished_span = self.get_finished_spans().by_name(f"ack {self.queue_consumer_name}")
        assert dict(ack_finished_span.attributes) == {
            MESSAGING_OPERATION_TYPE: "ack",
            MESSAGING_DESTINATION_NAME: self.fake_payload_headers.get("tshoot-destination"),
            MESSAGING_MESSAGE_CONVERSATION_ID: self.fake_payload_headers.get("correlation-id"),
            **self.span_host_attributes,
        }

    def test_should_create_nack_span_on_nack_listener_action(self, mocker):
        # Arrange
        publisher = build_publisher(f"test-publisher-{uuid4()}")
        publisher.send(queue=self.queue_consumer_name, body=self.fake_payload_body, headers=self.fake_payload_headers)

        # Act
        start_processing(
            self.queue_consumer_name,
            "tests.instrumentors.test_consumer_instrument.callback_nack",
            is_testing=True,
        )

        # Assert
        nack_finished_span = self.get_finished_spans().by_name(f"nack {self.queue_consumer_name}")

        assert dict(nack_finished_span.attributes) == {
            MESSAGING_OPERATION_TYPE: "nack",
            MESSAGING_DESTINATION_NAME: self.fake_payload_headers.get("tshoot-destination"),
            MESSAGING_MESSAGE_CONVERSATION_ID: self.fake_payload_headers.get("correlation-id"),
            **self.span_host_attributes,
        }

    def test_should_handle_exception_in_wrapper_on_message(self, mocker, caplog):
        # Arrange
        caplog.set_level(logging.WARNING)
        mocker.patch(
            "opentelemetry_instrumentation_django_stomp.instrumentors.consumer_instrument.get_span",
            side_effect=Exception("Test exception in wrapper_on_message"),
        )
        original_on_message = mocker.patch.object(self.listener, "on_message", wraps=self.listener.on_message)

        # Act
        self.listener.on_message(self.fake_frame)
        self.listener.shutdown_worker_pool()

        # Assert
        original_on_message.assert_called_once_with(self.fake_frame)
        assert "An exception occurred in the wrapper_on_message wrap." == caplog.messages[0]

    def test_should_handle_exception_in_common_ack_or_nack_span(self, mocker, caplog):
        # Arrange
        caplog.set_level(logging.WARNING)
        mocker.patch(
            "opentelemetry.trace.get_current_span", side_effect=Exception("Test exception in common_ack_or_nack_span")
        )
        publisher = build_publisher(f"test-publisher-{uuid4()}")
        publisher.send(queue=self.queue_consumer_name, body=self.fake_payload_body, headers=self.fake_payload_headers)

        # Act
        start_processing(
            self.queue_consumer_name,
            "tests.instrumentors.test_consumer_instrument.callback_ack",
            is_testing=True,
        )

        # Assert
        assert any(
            record.message == "An exception occurred while trying to set ack/nack span." for record in caplog.records
        )


class TestConsumerInstrumentHookRaises(TestConsumerBase):
    @staticmethod
    def hook_callback(span, body, headers):
        assert span.name == f"process {headers.get('tshoot-destination')}"
        raise CustomFakeException("fake exception")

    def test_should_log_exception_if_it_was_raised_inside_hook_function(self, mock_payload_size, caplog, mocker):
        # Arrange
        publisher = build_publisher(f"test-publisher-{uuid4()}")
        publisher.send(queue=self.queue_consumer_name, body=self.fake_payload_body, headers=self.fake_payload_headers)

        received_message = get_latest_message_from_destination_using_test_listener(self.queue_consumer_name)
        received_message_headers, received_message_body = received_message

        mocker.patch(
            "django_stomp.services.consumer.connect.StompConnection11.send_frame"
        )  # to not raise StompConnectionException
        fake_frame_with_trace_parent_header = StompFrame(
            cmd="FAKE_CMD", headers=received_message_headers, body=json.dumps(received_message_body)
        )

        caplog.set_level(logging.WARNING)

        # Act
        self.listener.on_message(fake_frame_with_trace_parent_header)
        self.listener.shutdown_worker_pool()

        # Assert
        finished_consumer_span = self.get_finished_spans().by_name(f"process {self.queue_consumer_name}")
        assert dict(finished_consumer_span.attributes) == self.expected_span_attributes(mock_payload_size)
        assert len(caplog.records) == 1
        assert caplog.records[0].message == "fake exception"
