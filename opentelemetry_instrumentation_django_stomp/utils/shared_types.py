import typing

from opentelemetry.trace.span import Span

CallbackHookT = typing.Optional[typing.Callable[[Span, typing.Dict, typing.Dict], None]]
