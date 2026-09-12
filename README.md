# agent-loop 🤖

An iterative **plan → execute → critique → improve** loop for writing and local media generation.

```text
goal → plan → execute → generate → critique → improve → repeat
```

## ✨ Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # fish: source .venv/bin/activate.fish
pip install -e .
cp .env.example .env
```

Set a provider in `.env`:

```env
AGENT_LOOP_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
AGENT_LOOP_MODEL=claude-sonnet-4-5
```

Then run:

```bash
agent-loop "Write a one-page product brief for a note-taking app"
agent-loop "Create a launch plan" -n 5
agent-loop --dry-run -n 1
```

🔒 Never commit `.env` or expose API keys.

## 🖼️ Image demo

The included SDXL workflow generated these real outputs. The vision critic reviews each result and guides the next iteration:

| First attempt | Improved attempt |
| --- | --- |
| ![First generated image](docs/images/empty-chinese-courtyard-dusk-nostalgia.png) | ![Improved generated image](docs/images/pastel-chinese-courtyard-dusk-liminal.png) |

**Prompt:** _A nostalgic liminal Chinese residential courtyard at dusk, faded pastel apartments, turquoise and pink lights, soft VHS bloom, millennial dream atmosphere._

Images are named automatically and saved under `runs/comfy/`.

## 🎨 Generate an image

Start ComfyUI:

```bash
cd /home/bowei/ComfyUI
.venv/bin/python main.py --listen 127.0.0.1 --port 8188 \
  --lowvram --disable-cuda-malloc --disable-async-offload \
  --cpu-vae --preview-method none
```

In another terminal:

```bash
cd /home/bowei/agent-loop
agent-loop "Create a cinematic product hero image" -n 2 \
  --comfy-workflow ./comfy-workflow.json \
  --comfy-prompt-node 6
```

The example uses SDXL at 768×768. A 6 GB GPU works best with batch size 1 and short runs.

## 🎥 Generate a video

The included LTX-2.3 workflow creates an MP4:

```bash
agent-loop "Create a short nostalgic liminal-space video with gentle camera movement" \
  -n 1 \
  --comfy-workflow ./ltx-video-workflow.json \
  --comfy-prompt-node 266 \
  --comfy-prompt-field value
```

Videos are saved under `runs/comfy/`. The current vision critic reviews image outputs; MP4 files remain available locally.

## 🧠 Providers

Native Anthropic is supported, along with OpenAI-compatible providers such as OpenAI, OpenRouter, Azure, and local servers. Configure the provider with `AGENT_LOOP_PROVIDER` and its API key in `.env`.

## 📁 Output locations

- `runs/*.json` — loop history and critiques
- `runs/comfy/` — generated images and videos
- `docs/images/` — README demo images

For a multi-user deployment, keep provider keys and ComfyUI behind a backend, queue GPU jobs, and store outputs in object storage.
