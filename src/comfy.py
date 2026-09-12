from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ComfyError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188", timeout: float = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    def _request(self, path: str, *, method: str = "GET", body: bytes | None = None) -> object:
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body else {},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read())
        except Exception as exc:
            raise ComfyError(f"ComfyUI request failed for {path}: {exc}") from exc

    def queue(self, workflow: dict) -> str:
        payload = json.dumps({"prompt": workflow, "client_id": self.client_id}).encode()
        result = self._request("/prompt", method="POST", body=payload)
        if not isinstance(result, dict) or "prompt_id" not in result:
            raise ComfyError(f"ComfyUI rejected workflow: {result}")
        return str(result["prompt_id"])

    def wait_for_media(self, prompt_id: str, output_dir: Path, poll_interval: float = 1.0) -> list[Path]:
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            history = self._request(f"/history/{prompt_id}")
            if isinstance(history, dict) and prompt_id in history:
                entry = history[prompt_id]
                status = entry.get("status", {}) if isinstance(entry, dict) else {}
                if status.get("status_str") == "error" or status.get("completed") is False:
                    raise ComfyError(f"ComfyUI workflow failed: {status}")
                media = self._download_media(entry, output_dir)
                if media:
                    return media
            time.sleep(poll_interval)
        raise ComfyError("Timed out waiting for ComfyUI workflow")

    def wait_for_images(self, prompt_id: str, output_dir: Path, poll_interval: float = 1.0) -> list[Path]:
        return self.wait_for_media(prompt_id, output_dir, poll_interval)

    def _download_media(self, entry: dict, output_dir: Path) -> list[Path]:
        paths: list[Path] = []
        outputs = entry.get("outputs", {})
        output_dir.mkdir(parents=True, exist_ok=True)
        for node_id, output in outputs.items():
            for media in output.get("images", []):
                query = urlencode({
                    "filename": media["filename"],
                    "subfolder": media.get("subfolder", ""),
                    "type": media.get("type", "output"),
                })
                request = Request(f"{self.base_url}/view?{query}")
                with urlopen(request, timeout=self.timeout) as response:
                    suffix = Path(media["filename"]).suffix or ".png"
                    destination = output_dir / f"node-{node_id}-{len(paths)}{suffix}"
                    destination.write_bytes(response.read())
                    paths.append(destination)
        return paths


def load_api_workflow(path: Path) -> dict:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    if "prompt" in workflow and isinstance(workflow["prompt"], dict):
        workflow = workflow["prompt"]
    if not isinstance(workflow, dict) or not all(isinstance(value, dict) and "class_type" in value for value in workflow.values()):
        raise ComfyError("Workflow must be exported from ComfyUI using Save (API Format)")
    return workflow


def set_prompt(workflow: dict, node_id: str, field: str, text: str) -> dict:
    updated = json.loads(json.dumps(workflow))
    node = updated.get(str(node_id))
    if not isinstance(node, dict) or field not in node.get("inputs", {}):
        raise ComfyError(f"Prompt node {node_id!r} has no input field {field!r}")
    node["inputs"][field] = text
    return updated
