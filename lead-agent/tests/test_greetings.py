"""Greeting fast-path for WhatsApp cheat sheet."""

import asyncio

import pytest

from app.agent import WELCOME_REPLY, _is_greeting, handle_message


@pytest.mark.parametrize(
    "message",
    [
        "hi",
        "Hi!",
        "Hello",
        "hello bhai",
        "namaste 🙏",
        "Hey there",
        "help please",
    ],
)
def test_is_greeting(message: str):
    assert _is_greeting(message)


@pytest.mark.parametrize(
    "message",
    ["list all my leads", "add lead Rahul phone 9876543210", "kavita ko call karo"],
)
def test_not_greeting(message: str):
    assert not _is_greeting(message)


def test_handle_message_returns_cheat_sheet_on_hi():
    reply = asyncio.run(handle_message("919111111111", "Hi!"))
    assert reply == WELCOME_REPLY
