"""Channels: the same agent behind SMS, USSD and voice (LOG4, GP FutureMakers).

The web app talks to `backend.agent.loop.run_turn` over SSE. A button phone
cannot, so this package turns each phone channel into ordinary agent turns and
turns the agent's event stream back into something a phone can show or say:

- `identity`  — a phone number becomes a stable, salted-hash farm/session id.
- `adapter`   — one channel turn: run the agent, collect text/menu/plan/finance.
- `sms_text`  — SMS length rules (GSM-7 vs UCS-2 segments) and the
                template-built plan summary. Numbers come from tool data only.
- `sms`       — SMS providers (SMSGate on an Android phone, bdapps, simulator).
- `ussd`      — the USSD menu state machine (never waits on the LLM).
- `voice`     — the Pipecat voice pipeline.
"""
