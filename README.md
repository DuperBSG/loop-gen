# agent-loop

Iterative **plan -> execute -> critique -> improve** loop for text and generated-image workflows. Each role is an LLM call. When ComfyUI is enabled, the loop generates an image locally, sends it to the vision-capable critic, and uses the critique to guide the next iteration.

## Local setup

```bash
python -m venv .venv
pip install -e .
cp .env.example .env
```

Activate the environment using the script for your shell:

```bash
# bash/zsh
source .venv/bin/activate

# fish
source .venv/bin/activate.fish
```

### Provider configuration

Native Anthropic:

```env
AGENT_LOOP_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key
AGENT_LOOP_MODEL=claude-sonnet-4-5
```

OpenAI-compatible providers, including OpenAI, OpenRouter, Azure, and local servers:

```env
AGENT_LOOP_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://api.openai.com/v1
AGENT_LOOP_MODEL=gpt-4o-mini
```

Do not commit `.env` or expose provider keys to users. If both keys are present, set `AGENT_LOOP_PROVIDER` explicitly.

## Run the loop

```bash
agent-loop "Write a one-page product brief for a note-taking app"
agent-loop "Create a launch plan" -n 5 -m gpt-4o-mini
agent-loop --dry-run -n 1   # no API calls
```

Runs are saved as JSON under `runs/` unless `--no-save` is passed. Generated ComfyUI media is saved under `runs/comfy/`.

## Image generation demo

This is a real output from the included SDXL workflow. The loop generated the image, saved it with an AI-generated filename, and attached it to the vision critic:

![Generated nostalgic Chinese courtyard](runs/comfy/iteration-1/empty-chinese-courtyard-dusk-nostalgia.png)

Prompt used:

> A nostalgic liminal Chinese residential courtyard at dusk, empty tiled plaza, faded pastel apartments, turquoise and pink fluorescent lights, soft VHS bloom, millennial dream atmosphere.

The loop can generate multiple iterations. Later iterations are saved separately so you can compare how the critique and improvement steps affect the result:

| Early iteration | Later iteration |
| --- | --- |
| ![Early generated image](runs/comfy/iteration-1/pastel-chinese-apartments-dusk-liminal.png) | ![Later generated image](runs/comfy/iteration-10/empty-chinese-courtyard-dusk-pastel.png) |

## ComfyUI image generation

The loop can submit a local ComfyUI workflow, download the generated image, ask the configured vision model to name it, and send the image back to the critic.

### Prepare ComfyUI

Install ComfyUI separately and start its local API server. For the current low-VRAM NVIDIA setup:

```bash
cd /home/bowei/ComfyUI
.venv/bin/python main.py --listen 127.0.0.1 --port 8188 \
  --lowvram --disable-cuda-malloc --disable-async-offload \
  --cpu-vae --preview-method none
```

The UI is available at `http://127.0.0.1:8188`.

### Configure a workflow

1. Open an image workflow in ComfyUI.
2. Choose **Save (API Format)**.
3. Save the JSON as `comfy-workflow.json` in this project.
4. Confirm the workflow's checkpoint and other models exist under ComfyUI's `models/` directories.
5. Identify the text prompt node ID and input field in the exported JSON.

The example workflow in this repository uses:

- `sd_xl_base_1.0.safetensors`
- 768x768 output
- node `6` as the positive prompt input
- one image per run

On a 6 GB GPU, use `--lowvram`, batch size 1, modest resolution, and short step counts. SDXL is slower than SD 1.5 and may require CPU offload.

### Video workflows

The included [`ltx-video-workflow.json`](/home/bowei/agent-loop/ltx-video-workflow.json) is an API-format LTX-2.3 text-to-video workflow. It writes MP4 files under `runs/comfy/` and can be run with:

```fish
agent-loop "Create a short nostalgic liminal-space video" -n 1 \
  --comfy-workflow ltx-video-workflow.json \
  --comfy-prompt-node 266 \
  --comfy-prompt-field value
```

Video files are tracked as run artifacts. The current critic sends generated images to the vision model; MP4 files remain available locally for playback or later frame extraction.

Run an image iteration:

```fish
agent-loop "Create a cinematic product hero image" -n 2 \
  --comfy-workflow /home/bowei/agent-loop/comfy-workflow.json \
  --comfy-prompt-node 6
```

If the prompt input is not called `text`:

```fish
agent-loop "Create a cinematic product hero image" -n 2 \
  --comfy-workflow comfy-workflow.json \
  --comfy-prompt-node 6 \
  --comfy-prompt-field prompt
```

The image flow is:

```text
LLM planner -> LLM executor -> ComfyUI image render -> vision critique -> improvement
```

The critic receives the generated image as a vision input. The CLI reports the attached image filename, and the run JSON records artifact paths.

## Recommended architecture for sharing this project

For multiple users, do not expose local ComfyUI or provider API keys. Use a hosted service:

```text
Users -> Web UI -> Backend API -> LLM provider
                         |
                         -> GPU worker running ComfyUI
```

Recommended production pieces:

- Web frontend: Next.js or another managed web UI
- Backend: FastAPI or equivalent
- LLM provider: Anthropic, OpenAI, OpenRouter, or a self-hosted endpoint behind a provider adapter
- GPU worker: ComfyUI on a cloud GPU
- Queue: Redis plus background workers for image jobs
- Storage: S3-compatible object storage for generated images
- Database: PostgreSQL for users, jobs, and run metadata
- Auth and billing: managed authentication plus per-user quotas

Keep provider credentials on the backend, enforce timeouts and usage limits, and queue GPU jobs instead of running them in web request handlers. The existing CLI/provider abstraction can serve as the core loop engine behind that API.
