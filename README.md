# HumanAuth

HumanAuth is a web-based human authentication demo that combines real-time face and hand landmark detection, challenge-response liveness checks, and low-latency WebSocket communication. This repository contains the frontend (Angular) and backend (Python) components, model files for MediaPipe-style processing, and helper scripts to run the demo locally.

## Table of Contents

1. Overview
2. High-level Architecture
3. Component Details
4. Data Flow
5. Local Setup \& Quick Start
6. Configuration
7. Performance \& Optimization
8. Security Considerations
9. Testing \& CI
10. Deployment Suggestions
11. Project Layout
12. Contributing
13. License

## 1. Overview

HumanAuth demonstrates a full stack system that performs human authentication by verifying live face and hand gestures. It uses on-server model processing for landmark extraction and a rich Angular frontend for capture, visualization, and user interaction.

## 2. High-level Architecture

- Frontend: Angular application responsible for camera capture, rendering face/hand meshes, user challenge UI, and communicating with the backend over WebSocket/HTTP.
- Backend: Python server (lightweight web framework such as Flask or FastAPI) that hosts MediaPipe-style model tasks, processes incoming frames, performs landmark extraction and liveness heuristics, and returns results in real time.
- Models: Prebuilt task files such as `face_landmarker.task` and `hand_landmarker.task` stored in the backend and loaded by the processing pipeline.
- Transport: WebSocket for low-latency, bidirectional streaming of frames and results; optional HTTP endpoints for health checks, configuration, or session management.
- Start script: `start.sh` in `humanauth-web` to orchestrate environment setup and start both servers.

## 3. Component Details

Frontend (`humanauth-web/frontend`)
- Angular app (served on port `4200` by default).
- Key files:
  - `frontend/src/app/auth-page/auth-page.component.ts` — main UI, challenge flow, visualization hooks.
  - `frontend/src/app/auth-page/auth-page.component.scss` — layout and CSS optimizations (video size, hardware-acceleration hints).
  - `frontend/src/app/services/camera.service.ts` — camera capture parameters (resolution, image quality, capture frequency).
- Responsibilities:
  - Acquire webcam frames via `getUserMedia`.
  - Draw camera preview and landmark visualizations on canvases.
  - Send capture frames to backend over WebSocket and apply server results to UI.

Backend (`humanauth-web/backend`)
- Python 3.8+ app (run `python app.py` in development).
- Key files:
  - `app.py` — server entrypoint, WebSocket handlers, model loader.
  - `requirements.txt` — Python dependencies (WebSocket, MediaPipe or wrapper, image utilities).
  - Model files: `face_landmarker.task`, `hand_landmarker.task`.
- Responsibilities:
  - Accept image frames via WebSocket.
  - Run model inference to return face/hand landmarks and liveness flags.
  - Maintain lightweight session/challenge state for each connected client.
  - Optionally provide HTTP endpoints for health and configuration.

Start script
- `start.sh` in `humanauth-web`:
  1. Checks dependencies
  2. Verifies model files exist
  3. Creates / activates Python venv and installs backend dependencies
  4. Launches backend then frontend dev server

## 4. Data Flow

1. User opens `http://localhost:4200` in browser.
2. Frontend requests camera access and captures frames at configured resolution (default `1280x720`).
3. Frames (or compressed frames) are sent to the backend via WebSocket.
4. Backend runs the loaded model tasks to detect face/hand landmarks and runs liveness heuristics (challenge matching, motion consistency).
5. Backend sends a compact JSON result payload back over WebSocket containing:
   - Landmarks (arrays of normalized coordinates)
   - Liveness / challenge result
   - Visualization hints (colors, indices)
6. Frontend updates visualization, challenge progress, and authentication state.

## 5. Local Setup \& Quick Start

Recommended quick start from repository root:

1. Navigate to `humanauth-web`:
   - `cd humanauth-web`
2. Make the start script executable and run it:
   - `chmod +x start.sh`
   - `./start.sh`

Manual startup:

Backend
- `cd humanauth-web/backend`
- `python3 -m venv venv`
- `source venv/bin/activate`
- `pip install -r requirements.txt`
- Ensure `face_landmarker.task` and `hand_landmarker.task` are in the backend directory
- `python app.py` (server listens on port `8000` by default)

Frontend
- `cd humanauth-web/frontend`
- `npm install`
- `npm start` (serves on `http://localhost:4200`)

Ensure both servers are running; open `http://localhost:4200`.

## 6. Configuration

- Backend URL: Update the frontend backend endpoint in `frontend/src/app/auth-page/auth-page.component.ts` if it differs from `http://localhost:8000`.
- Camera settings: Modify `frontend/src/app/services/camera.service.ts` for `getUserMedia` constraints (resolution, framerate) and capture quality.
- Model files: Keep `face_landmarker.task` and `hand_landmarker.task` in `humanauth-web/backend` or update `app.py` to point to their location.

## 7. Performance \& Optimization

Frontend optimizations
- Use `requestAnimationFrame` for render loops.
- Separate canvases: one for capture and one for visualization to avoid size/mode conflicts.
- Apply `transform: translate3d(0,0,0)` and `will-change` hints to force GPU compositing when beneficial.

Backend optimizations
- Batch or downscale incoming frames before inference (maintain enough resolution for landmarks).
- Reuse model sessions and avoid reloading on each request.
- Use asynchronous WebSocket handlers and non-blocking image IO.
- Consider running CPU-bound work in threads/process pool or on a GPU when available.

Quality vs latency tradeoffs
- Image quality default is `0.7` (balance). Lower to reduce bandwidth and inference time, raise for more accurate detection.

## 8. Security Considerations

- Do not expose model files or internal endpoints publicly.
- Run behind HTTPS in production; use secure WebSocket (`wss://`) to protect frame data.
- Implement authentication/authorization for production use.
- Rate limit and validate incoming frames to mitigate abuse.
- Sanitize and minimize stored PII; do not persist raw frames unless necessary and encrypted.

## 9. Testing \& CI

- Frontend: add unit tests for services/components using Angular TestBed and Karma/Jasmine.
- Backend: add unit tests for model loader, inference outputs, and WebSocket handlers using pytest and test clients.
- Add end-to-end tests to simulate camera input and validate full flow (tools like Playwright can mock media devices).
- CI: include lint and test steps; optionally build artifacts for containerization.

## 10. Deployment Suggestions

- Containerize backend with a small base image (Python slim). Mount model files or include them in the image.
- Serve frontend as static assets behind a CDN or Nginx, and proxy WebSocket traffic to the backend.
- Use TLS termination and a reverse proxy (Nginx) to handle `wss` and HTTP(S).
- Scale backend horizontally behind a load balancer; use sticky sessions or session store for WebSocket affinity.

## 11. Project Layout

A representative layout:

- `HumanAuth/` \- repository root
  - `humanauth-web/`
    - `start.sh` \- start orchestration script
    - `frontend/`
      - `src/`
        - `app/`
          - `auth-page/`
            - `auth-page.component.ts`
            - `auth-page.component.scss`
          - `services/`
            - `camera.service.ts`
      - `package.json`
    - `backend/`
      - `app.py`
      - `requirements.txt`
      - `face_landmarker.task`
      - `hand_landmarker.task`
  - `LICENSE`
  - `README.md` \- (this file)

## 12. Contributing

- Follow the repository coding style and add tests for new features.
- Open issues for bugs or design discussions.
- Use branches and PRs for changes; include a clear description and testing steps.

## 13. License

This project is licensed under the MIT License. See `LICENSE` for details.

---

If files or paths differ in your copy of the repo, update configuration values in `frontend/src/app/auth-page/auth-page.component.ts` and `humanauth-web/start.sh` accordingly.
