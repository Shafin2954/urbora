"""SMS keyword commands for the marketplaces ("বিক্রি ...", order confirmations).

Returns the SMS reply text when a message is a marketplace command, or None to
let the agent answer it. Commands are registered as the marketplaces land.
"""

from __future__ import annotations


def try_handle(local_msisdn: str, text: str) -> str | None:
    return None
