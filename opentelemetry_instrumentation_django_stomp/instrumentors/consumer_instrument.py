import logging
import typing

import wrapt

from django_stomp.services.consumer import Listener
from django_stomp.settings import STOMP_PROCESS_MSG_WORKERS
from opentelemetry import context
from opentelemetry import propagate
from opentelemetry import trace
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.sdk.trace import Tracer
from opentelemetry.semconv.trace import MessagingOperationValues
from opentelemetry.trace import SpanKind
from stomp.connect import StompConnection11

from opentelemetry_instrumentation_django_stomp.utils.django_stomp_getter import DjangoStompGetter
from opentelemetry_instrumentation_django_stomp.utils.shared_types import CallbackHookT
from opentelemetry_instrumentation_django_stomp.utils.span import enrich_span_with_host_data
from opentelemetry_instrumentation_django_stomp.utils.span import get_span
from opentelemetry_instrumentation_django_stomp.utils.traced_thread_pool_executor import TracedThreadPoolExecutor

_django_stomp_getter = DjangoStompGetter()

_logger = logging.getLogger(__name__)


class ConsumerInstrument:
    @staticmethod
    def instrument(tracer: Tracer, callback_hook: CallbackHookT = None):
        """Instrumentor function to create span and instrument consumer"""

        def wrapper_on_message(wrapped, instance, args, kwargs):
            frame = args[0]
            headers, body = frame.headers, frame.body

            ctx = propagate.extract(headers, getter=_django_stomp_getter)
            if not ctx:
                ctx = context.get_current()
            token = context.attach(ctx)

            span = get_span(
                tracer=tracer,
                destination=headers.get("tshoot-destination"),
                span_kind=SpanKind.CONSUMER,
                headers=headers,
                body=body,
                span_name="CONSUMER",
                operation=str(MessagingOperationValues.RECEIVE.value),
            )

            try:
                with trace.use_span(span, end_on_exit=True):
                    if callback_hook:
                        try:
                            callback_hook(span, body, headers)
                        except Exception as hook_exception:  # pylint: disable=W0703
                            _logger.exception(hook_exception)
                    return wrapped(*args, **kwargs)
            finally:
                context.detach(token)

        def wrapper_create_new_worker_executor(wrapped, instance, args, kwargs):
            return TracedThreadPoolExecutor(
                tracer=trace.get_tracer(__name__),
                max_workers=STOMP_PROCESS_MSG_WORKERS,
                thread_name_prefix=instance._subscription_id,
            )

        def common_ack_or_nack_span(span_name: str, wrapped_function: typing.Callable):
            span = tracer.start_span(name=span_name, kind=SpanKind.CONSUMER)
            enrich_span_with_host_data(span)
            with trace.use_span(span, end_on_exit=True):
                return wrapped_function

        def wrapper_nack(wrapped, instance, args, kwargs):
            return common_ack_or_nack_span("NACK", wrapped(*args, **kwargs))

        def wrapper_ack(wrapped, instance, args, kwargs):
            return common_ack_or_nack_span("ACK", wrapped(*args, **kwargs))

        wrapt.wrap_function_wrapper(Listener, "on_message", wrapper_on_message)
        wrapt.wrap_function_wrapper(Listener, "_create_new_worker_executor", wrapper_create_new_worker_executor)
        wrapt.wrap_function_wrapper(StompConnection11, "nack", wrapper_nack)
        wrapt.wrap_function_wrapper(StompConnection11, "ack", wrapper_ack)

    @staticmethod
    def uninstrument():
        unwrap(Listener, "on_message")
        unwrap(Listener, "_create_new_worker_executor")
        unwrap(StompConnection11, "nack")
        unwrap(StompConnection11, "ack")
