"""Voice line: speech in, agent turn, speech out, SMS summary after hang-up.

Two transports share `turn.voice_turn`:
- the browser phone emulator (push-to-talk, half-duplex) — works today;
- a USB 4G modem (Quectel EC2x) for real phone calls — planned; the driver
  waits for the hardware (LOG.md [03:10]).
"""
