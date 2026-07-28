"""
API-key auth for inbound callers of the gateway - deliberately a different
mechanism than the OAuth2 JWT flow used for the outbound enterprise
integration (src/integrations/enterprise_api/), since these are genuinely
different boundaries: this side authenticates internal client applications
(e.g. a case-worker portal) calling ClaimAssist, not ClaimAssist calling out
to another system.
"""

import os

# A real gateway would issue/manage keys per client application via a
# proper secrets store or database - a plain dict is fine here, since the
# point being demonstrated is the gateway boundary itself (auth + rate
# limiting in front of the agent), not key management infrastructure.
API_KEYS = {
    os.environ["GATEWAY_API_KEY"]: os.environ.get("GATEWAY_CLIENT_NAME", "case-worker-portal"),
}


def authenticate_api_key(api_key: str) -> str | None:
    """Returns the client name if the key is valid, None otherwise."""
    return API_KEYS.get(api_key)
