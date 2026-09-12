# ModelScope International deployment

Fork of moesnow/March7thAssistant at `b0be473cfd24510d894c96e27964ca52268a80f0`.
WebUI, multi-account scheduling, QR login and cloud-game integration adapted from
[StarEdge-Studio/March7thAssistant-Docker-Enhance](https://github.com/StarEdge-Studio/March7thAssistant-Docker-Enhance)
at `102d65de2decf7bd92e4d6ef4b8275cb5ac986cb`, under the existing GPL-3.0 license.

Build workflow publishes `ghcr.io/ishansiy/march7thassistant:latest` and an immutable commit tag.
The Studio Dockerfile references the published image by digest. No application build is needed on ModelScope.

Set the Studio secret `WEBUI_TOKEN` to a strong random value. No default password is accepted.
HTTP listens on port 7860. The WebUI uses `X-M7A-Token`, avoiding ModelScope's reserved Authorization header.

All mutable application state is linked to `/mnt/workspace`: `webui/data` (accounts, settings,
per-account profiles and task history), logs, screenshots, config, browser UserProfile,
temporary files and caches. Existing files are migrated without overwriting persisted files;
conflicting legacy files remain in a timestamped backup under `/mnt/workspace/migration-backups`.
Code, Python dependencies, browser binaries and OCR assets remain in the image.
Never rename or transfer a Studio as a persistence strategy; platform storage retention is separate.

Open the WebUI, enter WEBUI_TOKEN, add an account and scan the cloud game's QR code.
Deployment does not log in to the game or start a game task automatically.
