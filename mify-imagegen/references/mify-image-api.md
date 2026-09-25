<!-- feishu: https://mi.feishu.cn/wiki/XiGMw1X4giKWrGk1eTScVrMYnCc -->

# Mify Image API Source Notes

This reference summarizes the Feishu wiki page titled `【调用示例】图片生成`.

## Supported OpenAI Provider

| Provider | Model |
| --- | --- |
| `azure_openai` | `gpt-image-2` |

## Generate

```bash
curl --location --request POST 'http://model.mify.ai.srv/v1/images/generations' \
  --header 'Authorization: Bearer your_key' \
  --header 'X-Model-Provider-Id: azure_openai' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "model": "gpt-image-2",
    "prompt": "A clean editorial poster of a futuristic electric scooter parked beside a glass office building at sunrise, realistic reflections, crisp details, no text, no watermark.",
    "size": "1024x1024",
    "quality": "low",
    "n": 1
  }'
```

## Edit

```bash
curl --location --request POST 'http://model.mify.ai.srv/v1/images/edits' \
  --header 'Authorization: Bearer your_key' \
  --header 'X-Model-Provider-Id: azure_openai' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "model": "gpt-image-2",
    "prompt": "Change the background of this image to pure white.",
    "image_url": "data:image/jpeg;base64,...",
    "size": "1024x1024",
    "n": 1
  }'
```

The skill CLI implements this contract with stdlib HTTP, reads the Mify token locally, and writes returned `b64_json` or URL image outputs to disk.
