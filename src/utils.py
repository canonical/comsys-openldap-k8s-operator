# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Define helpers methods."""

import functools
import secrets
import string


def log_event_handler(logger):
    """Log with the provided logger when a event handler method is executed.

    Args:
        logger: logger used to log events.

    Returns:
        Decorator wrapper.
    """

    def decorator(method):
        """Log decorator wrapper.

        Args:
            method: method wrapped by the decorator.

        Returns:
            Decorated method.
        """

        @functools.wraps(method)
        def decorated(self, event):
            """Log decorator method.

            Args:
                event: The event triggered when the relation changes.

            Returns:
                Decorated method.
            """
            logger.info(
                f"* running {self.__class__.__name__}.{method.__name__}"
            )
            try:
                return method(self, event)
            finally:
                logger.info(
                    f"* completed {self.__class__.__name__}.{method.__name__}"
                )

        return decorated

    return decorator


def random_string(length) -> str:
    """Create randomized string for use as app password.

    Args:
        length: number of characters to generate

    Returns:
        String of randomized letter+digit characters
    """
    return "".join(
        [
            secrets.choice(string.ascii_letters + string.digits)
            for _ in range(length)
        ]
    )
