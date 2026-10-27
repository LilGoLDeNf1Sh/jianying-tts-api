class TTSError(RuntimeError):
    """Safe, user-facing synthesis failure."""


class BridgeUnavailable(TTSError):
    """Jianying is not running or its local bridge is unavailable."""


class VoiceNotFound(TTSError):
    """The requested voice is not in the synchronized catalog."""


class VoiceUnavailable(TTSError):
    """The current account is not entitled to use this voice."""


class UpstreamError(TTSError):
    """Jianying rejected a request or returned malformed data."""
