import logging
import threading
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
from opentelemetry.trace import Status
from opentelemetry.trace import StatusCode
from stomp.connect import StompConnection11

from ..utils.django_stomp_getter import DjangoStompGetter
from ..utils.shared_types import CallbackHookT
from ..utils.span import get_messaging_ack_nack_span
from ..utils.span import get_span
from ..utils.traced_thread_pool_executor import TracedThreadPoolExecutor

_django_stomp_getter = DjangoStompGetter()

_logger = logging.getLogger(__name__)

_thread_local = threading.local()


class ConsumerInstrument:
    @staticmethod
    def instrument(tracer: Tracer, callback_hook: CallbackHookT = None):
        """Instrumentor function to create span and instrument consumer"""

        def wrapper_on_message(wrapped, instance, args, kwargs):
            try:
                frame = args[0]
                headers, body = frame.headers, frame.body

                ctx = propagate.extract(headers, getter=_django_stomp_getter)
                if not ctx:
                    ctx = context.get_current()
                token = context.attach(ctx)

                destination = headers.get("tshoot-destination")
                span = get_span(
                    tracer=tracer,
                    destination=destination,
                    span_kind=SpanKind.CONSUMER,
                    headers=headers,
                    body=body,
                    span_name=f"process {destination}",
                    operation=str(MessagingOperationValues.RECEIVE.value),
                )

            except Exception as unmapped_exception:
                _logger.warning("An exception occurred in the wrapper_on_message wrap.", exc_info=unmapped_exception)
                return wrapped(*args, **kwargs)

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

        def wrapper_create_new_worker_executor(wrapped, instance, *args, **kwargs):
            return TracedThreadPoolExecutor(
                tracer=trace.get_tracer(__name__),
                max_workers=STOMP_PROCESS_MSG_WORKERS,
                thread_name_prefix=instance._subscription_id,
            )

        def common_ack_or_nack_span(span_event_name: str, span_status: Status, wrapped_function: typing.Callable):
            try:
                process_span = trace.get_current_span()
                if process_span and process_span.is_recording():
                    process_span.add_event(span_event_name)
                    process_span.set_status(span_status)

                ack_nack_span = get_messaging_ack_nack_span(
                    tracer=tracer,
                    operation="ack" if span_event_name == "message.ack" else "nack",
                    process_span=process_span,
                )
                if ack_nack_span and ack_nack_span.is_recording():
                    ack_nack_span.add_event(span_event_name)
                    ack_nack_span.set_status(span_status)
                    ack_nack_span.end()
            except Exception as unmapped_exception:
                _logger.warning("An exception occurred while trying to set ack/nack span.", exc_info=unmapped_exception)
            finally:
                return wrapped_function

        def wrapper_nack(wrapped, instance, args, kwargs):
            return common_ack_or_nack_span("message.nack", Status(StatusCode.ERROR), wrapped(*args, **kwargs))

        def wrapper_ack(wrapped, instance, args, kwargs):
            return common_ack_or_nack_span("message.ack", Status(StatusCode.OK), wrapped(*args, **kwargs))

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
