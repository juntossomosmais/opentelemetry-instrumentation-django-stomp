import typing

from django_stomp.builder import build_listener


class CustomFakeException(Exception):
    pass


def get_latest_message_from_destination_using_test_listener(destination: str) -> typing.Dict:
    """
    Gets the latest message using the test listener utility. It does not ack the message
    on the destination queue.
    [!]: It makes a test hang forever if a message never arrives at the destination.
    """
    evaluation_consumer = build_listener(destination, is_testing=True)
    test_listener = evaluation_consumer._test_listener
    evaluation_consumer.start(wait_forever=False)

    # may wait forever if the msg never arrives
    test_listener.wait_for_message()
    received_message = test_listener.get_latest_message()

    return received_message
