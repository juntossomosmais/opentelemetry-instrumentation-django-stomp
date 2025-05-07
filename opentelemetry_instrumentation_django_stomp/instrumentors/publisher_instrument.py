import logging

import wrapt

from django_stomp.services.producer import Publisher
from opentelemetry import propagate
from opentelemetry import trace
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.sdk.trace import Tracer
from opentelemetry.semconv.trace import MessagingOperationValues
from opentelemetry.trace import SpanKind

from ..utils.shared_types import CallbackHookT
from ..utils.span import get_span

_logger = logging.getLogger(__name__)


class PublisherInstrument:
    @staticmethod
    def instrument(tracer: Tracer, callback_hook: CallbackHookT = None):
        """Instrumentor to create span and instrument publisher"""

        def wrapper_publisher(wrapped, instance, args, kwargs):
            try:
                payload = args[0]
                headers, body = payload.get("headers"), payload.get("body")
                destination = headers.get("tshoot-destination")
                span = get_span(
                    tracer=tracer,
                    destination=headers.get("tshoot-destination"),
                    span_kind=SpanKind.PRODUCER,
                    headers=headers,
                    body=body,
                    span_name=f"send {destination}",
                    operation=str(MessagingOperationValues.PUBLISH.value),
                )

                with trace.use_span(span, end_on_exit=True):
                    if span.is_recording():
                        propagate.inject(headers)
                        if callback_hook:
                            try:
                                callback_hook(span, body, headers)
                            except Exception as hook_exception:  # pylint: disable=W0703
                                _logger.exception(hook_exception)
                    return wrapped(*args, **kwargs)
            except Exception as unmapped_exception:
                _logger.warning("An exception occurred in the wrapper_publisher wrap.", exc_info=unmapped_exception)
                return wrapped(*args, **kwargs)

        wrapt.wrap_function_wrapper(Publisher, "_send_to_broker_without_retry_attempts", wrapper_publisher)
        wrapt.wrap_function_wrapper(Publisher, "_send_to_broker", wrapper_publisher)

    @staticmethod
    def uninstrument():
        """Uninstrument publisher functions from django-stomp"""
        unwrap(Publisher, "_send_to_broker_without_retry_attempts")
        unwrap(Publisher, "_send_to_broker")
