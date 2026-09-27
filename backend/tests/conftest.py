"""Keep tests hermetic: a developer's real keys in .env.local must not switch
providers (e.g. send test audio to Sarvam) or turn on live channels."""

import pytest

PROVIDER_VARS = (
    "SARVAM_API_KEY", "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION", "VOICE_STT", "VOICE_TTS",
    "SMS_PROVIDER", "SMSGATE_URL", "SMSGATE_USER", "SMSGATE_PASSWORD", "SMSGATE_SIGNING_KEY",
    "CHANNEL_EMULATOR_ENABLED", "ALERT_SMS_ENABLED", "BRIDGE_TOKEN", "PHONELINK_ENABLED",
)


@pytest.fixture(autouse=True)
def _hermetic_providers(monkeypatch):
    for var in PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)
