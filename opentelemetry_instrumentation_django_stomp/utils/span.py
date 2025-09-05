import json
import sys
import typing

from django.conf import settings
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace import Tracer
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_DESTINATION_NAME
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_MESSAGE_BODY_SIZE
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_MESSAGE_CONVERSATION_ID
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_OPERATION_TYPE
from opentelemetry.semconv._incubating.attributes.messaging_attributes import MESSAGING_SYSTEM
from opentelemetry.semconv._incubating.attributes.net_attributes import NET_PEER_NAME
from opentelemetry.semconv._incubating.attributes.net_attributes import NET_PEER_PORT
from opentelemetry.trace import SpanKind


def enrich_span_with_host_data(span: Span):
    """Helper function add broker SpanAttributes"""
    system = getattr(settings, "STOMP_SYSTEM", None) or "rabbitmq"
    attributes = {
        NET_PEER_NAME: settings.STOMP_SERVER_HOST,
        NET_PEER_PORT: settings.STOMP_SERVER_PORT,
        MESSAGING_SYSTEM: system,
    }
    span.set_attributes(attributes)


def enrich_span(
    span: Span,
    operation: typing.Optional[str],
    destination: str,
    headers: typing.Dict,
    body: typing.Dict,
) -> None:
    """Helper function add SpanAttributes"""
    attributes = {
        MESSAGING_DESTINATION_NAME: destination,
        MESSAGING_MESSAGE_CONVERSATION_ID: str(headers.get("correlation-id")),
        MESSAGING_MESSAGE_BODY_SIZE: sys.getsizeof(json.dumps(body)),
    }
    if operation is not None:
        attributes.update({MESSAGING_OPERATION_TYPE: operation})
    span.set_attributes(attributes)
    enrich_span_with_host_data(span)


def get_span(
    tracer: Tracer,
    destination: str,
    span_kind: SpanKind,
    headers: typing.Dict,
    body: typing.Dict,
    span_name: str,
    operation: typing.Optional[str] = None,
) -> Span:
    """Helper function to mount span and call function to set SpanAttributes"""
    span = tracer.start_span(name=span_name, kind=span_kind)
    if span.is_recording():
        enrich_span(
            span=span,
            operation=operation,
            destination=destination,
            headers=headers,
            body=body,
        )
    return span


def get_messaging_ack_nack_span(
    tracer: Tracer,
    operation: str,  # ack or nack
    process_span: Span,
) -> Span:
    """Helper function to mount span and call function to set SpanAttributes"""
    destination = process_span._attributes.get(MESSAGING_DESTINATION_NAME, "UNKNOWN")
    conversation_id = process_span._attributes.get(MESSAGING_MESSAGE_CONVERSATION_ID, "UNKNOWN")
    span_name = f"ack {destination}" if operation == "ack" else f"nack {destination}"

    span = tracer.start_span(name=span_name, kind=SpanKind.CONSUMER)
    if span.is_recording():
        attributes = {
            MESSAGING_OPERATION_TYPE: operation,
            MESSAGING_DESTINATION_NAME: destination,
            MESSAGING_MESSAGE_CONVERSATION_ID: conversation_id,
        }
        span.set_attributes(attributes)
        enrich_span_with_host_data(span)
    return span
