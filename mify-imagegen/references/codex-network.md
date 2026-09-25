# Mify network and token notes

This file is for Mify CLI mode. Read it when `scripts/image_gen.py` fails because it cannot find a token or cannot reach the Mify image gateway.

## Authentication

The CLI reads the first available token source:

1. `MIFY_IMAGE_API_KEY`
2. `MIFY_API_KEY`
3. `~/.config/mify/credentials` containing `export MIFY_API_KEY=...`

Never ask the user to paste the token in chat. If the token is missing, use the existing `mify-model-gateway` token setup flow or ask the user to configure the token locally.

## Network

The default image gateway is:

```text
http://model.mify.ai.srv/v1
```

The provider header is:

```text
X-Model-Provider-Id: azure_openai
```

Useful overrides:

```bash
export MIFY_IMAGE_BASE_URL="http://model.mify.ai.srv/v1"
export MIFY_IMAGE_PROVIDER_ID="azure_openai"
export MIFY_IMAGE_TIMEOUT="300"
```

## Troubleshooting

- `Missing Mify API key`: token is not in env and no readable credentials file exists.
- `HTTP 401`: token invalid or expired.
- `HTTP 400`: unsupported parameter, invalid size, or payload mismatch.
- DNS/timeout: not on the required company network/VPN or gateway unavailable.

Start with a dry-run to confirm payload shape:

```bash
python "$IMAGE_GEN" generate --prompt "Test" --size 1024x1024 --dry-run
```
