import json
import sys
import typing

from django.conf import settings
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace import Tracer
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.trace import SpanKind


def enrich_span_with_host_data(span: Span):
    """Helper function add broker SpanAttributes"""
    system = getattr(settings, "STOMP_SYSTEM", None) or "rabbitmq"
    attributes = {
        SpanAttributes.NET_PEER_NAME: settings.STOMP_SERVER_HOST,
        SpanAttributes.NET_PEER_PORT: settings.STOMP_SERVER_PORT,
        SpanAttributes.MESSAGING_SYSTEM: system,
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
        SpanAttributes.MESSAGING_DESTINATION: destination,
        SpanAttributes.MESSAGING_CONVERSATION_ID: str(headers.get("correlation-id")),
        SpanAttributes.MESSAGING_MESSAGE_PAYLOAD_SIZE_BYTES: sys.getsizeof(json.dumps(body)),
    }
    if operation is not None:
        attributes.update({SpanAttributes.MESSAGING_OPERATION: operation})
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
