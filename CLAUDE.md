# Avid DNxHR to Instagram - Project Specifications

## Project Context
You are developing **Avid DNxHR to Instagram**, a self-hosted, dockerized transcoding application tailored for **Raspberry Pi 4 (ARM64)**. It ingests high-quality master files exported from **DaVinci Resolve 21** (specifically Avid DNxHR format) and converts them into an Instagram and WhatsApp compatible format (H.264/AAC MP4) without changing the original resolution or sacrificing perceived visual quality.

## System Architecture & Constraints
- **Target Hardware:** Raspberry Pi 4 (ARM64 architecture). Code optimization must account for thermal and resource limits.
- **CPU Resource Allocation:** The transcoding engine (FFmpeg) must be constrained to utilize **exactly 3 out of the 4 CPU cores** to ensure system stability.
- **Input Directory (Host):** `/apps/TRANSCODING/inputs` -> Mapped to `/inputs` inside the container.
- **Output Directory (Host):** `/apps/TRANSCODING/outputs` -> Mapped to `/outputs` inside the container.

## Application Workflow & Features
1. **Ingestion (Dual-Method):**
   - **Shared Folder:** Detects files directly placed in the input directory.
   - **Web UI:** Provides a clean interface with a Dropzone/upload button. The web upload includes a real-time **Progress Bar** and **ETA**.
2. **File Selection:** The web panel must list all available files in the input directory, allowing the user to select one for processing.
3. **Trigger:** Conversion **ONLY** starts when the user explicitly clicks the **"CONVERTIR"** button.
4. **Transcoding Requirements (FFmpeg):**
   - **Video:** Maintain original resolution. Convert to H.264 using high-quality visually lossless parameters matching Instagram specifications (e.g., `-c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p`).
   - **Audio:** Must be transcoded to an Instagram and WhatsApp friendly format (AAC stereo, e.g., `-c:a aac -b:a 256k`).
   - **Progress Monitoring:** The UI must display a real-time **Progress Bar** and **ETA** during the transcoding stage.
5. **Post-Processing Checkbox:**
   - A toggle labelled **"Borrar archivo de input al finalizar con éxito"** (Disabled by default).
   - If checked and transcoding succeeds, the source file must be safely deleted.
6. **Notifications (ntfy):**
   - On completion (Success or Failure), dispatch a payload to **ntfy** on the topic `pi-transcoding`.

## Docker Configuration (Strict Rules)
The final deliverable must be a standalone Docker setup. All configuration values, credentials, and environmental constraints **MUST be defined in the `docker-compose.yml` file and NEVER hardcoded** in the source code.

### Required Environment Variables:
- `CPU_CORES=3` (Passed to FFmpeg `-threads` or Docker resource limits)
- `NTFY_TOPIC=pi-transcoding`
- `NTFY_URL=https://ntfy.sh` (or custom server instance)
- `FFMPEG_CRF=18`
- `FFMPEG_PRESET=slow`

## Project Commands
- **Run Development Instance:** `docker compose up --build`
- **Check Container Logs:** `docker compose logs -f`
- **Reindex Project Graph:** `graphify .`

## Code & AI Guidelines
- **Graphify Integration:** Always query the codebase structure via `/graphify .` before altering multi-file architectures.
- **FFmpeg Handling:** Wrap all subprocess executions using strict Python exception handling (`subprocess.CalledProcessError`) to accurately catch and report conversion failures to `ntfy`.
- **Language:** Code comments and documentation must be in English. Console responses and UI elements must be in Spanish.
