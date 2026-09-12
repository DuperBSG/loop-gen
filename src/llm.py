from __future__ import annotations

import base64
import mimetypes
import re

from config import (
    ANTHROPIC_API_KEY,
    BASE_URL,
    DEFAULT_MODEL,
    OPENAI_API_KEY,
    PROVIDER,
)

_client = None


def get_client():
    global _client
    if _client is None:
        if PROVIDER == "anthropic":
            if not ANTHROPIC_API_KEY:
                raise SystemExit(
                    "ANTHROPIC_API_KEY is not set. Copy .env.example to .env "
                    "or pass --dry-run."
                )
            from anthropic import Anthropic

            _client = Anthropic(api_key=ANTHROPIC_API_KEY)
        elif not OPENAI_API_KEY:
            raise SystemExit(
                "OPENAI_API_KEY is not set. Copy .env.example to .env or pass --dry-run."
            )
        else:
            from openai import OpenAI

            kwargs: dict = {"api_key": OPENAI_API_KEY}
            if BASE_URL:
                kwargs["base_url"] = BASE_URL
            _client = OpenAI(**kwargs)
    return _client


def _image_data(path: str) -> tuple[str, str]:
    media_type = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as handle:
        data = base64.b64encode(handle.read()).decode("ascii")
    return media_type, data


def _anthropic_content(user: str, image_paths: list[str]) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": user}]
    for path in image_paths:
        media_type, data = _image_data(path)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": data},
        })
    return content


def _openai_content(user: str, image_paths: list[str]) -> list[dict]:
    content: list[dict] = [{"type": "text", "text": user}]
    for path in image_paths:
        media_type, data = _image_data(path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{media_type};base64,{data}"},
        })
    return content


def complete(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.4,
    image_paths: list[str] | None = None,
) -> str:
    image_paths = image_paths or []
    if PROVIDER == "anthropic":
        response = get_client().messages.create(
            model=model or DEFAULT_MODEL,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": _anthropic_content(user, image_paths)}],
        )
        return "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()

    response = get_client().chat.completions.create(
        model=model or DEFAULT_MODEL,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": _openai_content(user, image_paths)},
        ],
    )
    content = response.choices[0].message.content
    return (content or "").strip()


def name_image(path: str, goal: str, *, model: str | None = None) -> str:
    response = complete(
        "You name generated images for a local file library.",
        "Return only a short filesystem-safe name, 3 to 7 lowercase words separated by hyphens. "
        f"Goal: {goal}",
        model=model,
        temperature=0.2,
        image_paths=[path],
    )
    name = re.sub(r"[^a-z0-9]+", "-", response.lower()).strip("-")
    return name[:80] or "generated-image"
