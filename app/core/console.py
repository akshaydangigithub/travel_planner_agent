"""Console interaction helpers.

Isolated here so interactive nodes stay testable and the rest of the
application never touches ``input``/``print`` directly.
"""


def show(message: str) -> None:
    """Write a message meant for the person operating the planner."""

    print(message)


def prompt(question: str) -> str:
    """Ask the user a question and return their answer."""

    return input(question)
