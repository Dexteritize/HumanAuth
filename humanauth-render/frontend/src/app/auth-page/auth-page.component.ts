import { Component, ElementRef, ViewChild, OnDestroy, NgZone, HostListener } from "@angular/core";
import { CommonModule } from "@angular/common";
import { HttpClientModule } from "@angular/common/http";
import { CameraService } from "../services/camera.service";
import { AuthService, AuthResult, SessionSummary } from "../services/auth.service";
import { environment } from "../../environments/environment";

// Face mesh connections for drawing
const FACE_CONNECTIONS = [
  // Lips outer
  [61, 146], [146, 91], [91, 181], [181, 84], [84, 17],
  [17, 314], [314, 405], [405, 321], [321, 375], [375, 291],
  [61, 185], [185, 40], [40, 39], [39, 37], [37, 0], [0, 267],
  [267, 269], [269, 270], [270, 409], [409, 291],
  // Eyes
  [33, 7], [7, 163], [163, 144], [144, 145], [145, 153], [153, 154], [154, 155], [155, 133], [133, 173], [173, 157], [157, 158], [158, 159], [159, 160], [160, 161], [161, 246], [246, 33],
  [263, 249], [249, 390], [390, 373], [373, 374], [374, 380], [380, 381], [381, 382], [382, 362], [362, 398], [398, 384], [384, 385], [385, 386], [386, 387], [387, 388], [388, 466], [466, 263],
  // Eyebrows
  [70, 63], [63, 105], [105, 66], [66, 107], [107, 55], [55, 65], [65, 52], [52, 53], [53, 46],
  [300, 293], [293, 334], [334, 296], [296, 336], [336, 285], [285, 295], [295, 282], [282, 283], [283, 276],
  // Nose
  [168, 6], [6, 197], [197, 195], [195, 5], [5, 4], [4, 45], [45, 220], [220, 115], [115, 48],
  [48, 64], [64, 98], [98, 97], [97, 2], [2, 326], [326, 327], [327, 278], [278, 294], [294, 331], [331, 297], [297, 338], [338, 10], [10, 151], [151, 9], [9, 8], [8, 168],
  // Face contour
  [10, 338], [338, 297], [297, 332], [332, 284], [284, 251], [251, 389], [389, 356], [356, 454], [454, 323], [323, 361], [361, 288], [288, 397], [397, 365], [365, 379], [379, 378], [378, 400], [400, 377], [377, 152], [152, 148], [148, 176], [176, 149], [149, 150], [150, 136], [136, 172], [172, 58], [58, 132], [132, 93], [93, 234], [234, 127], [127, 162], [162, 21], [21, 54], [54, 103], [103, 67], [67, 109], [109, 10]
];

// Hand connections for drawing
const HAND_CONNECTIONS = [
  // Thumb
  [0, 1], [1, 2], [2, 3], [3, 4],
  // Index finger
  [0, 5], [5, 6], [6, 7], [7, 8],
  // Middle finger
  [0, 9], [9, 10], [10, 11], [11, 12],
  // Ring finger
  [0, 13], [13, 14], [14, 15], [15, 16],
  // Pinky
  [0, 17], [17, 18], [18, 19], [19, 20],
  // Palm
  [0, 5], [5, 9], [9, 13], [13, 17]
];

type Landmark = { x: number; y: number; z?: number };
type Scores = Record<string, number>;

enum UiState {
  Idle = "idle",
  Starting = "starting",
  Running = "running",
  Success = "success",
  Error = "error",
  Stopped = "stopped",
}

@Component({
  selector: "app-auth-page",
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  templateUrl: "./auth-page.component.html",
  styleUrls: ["./auth-page.component.scss"],
})
export class AuthPageComponent implements OnDestroy {
  @ViewChild("video", { static: true }) video!: ElementRef<HTMLVideoElement>;
  @ViewChild("canvas", { static: true }) canvas!: ElementRef<HTMLCanvasElement>;

  backendUrl = environment.backendUrl;

  // Keep these for template compatibility
  running = false;
  result?: AuthResult;
  error?: string;

  // New UX-focused state (optional to bind in template)
  uiState: UiState = UiState.Idle;
  statusTitle = "Ready";
  statusSubtitle = "Press Start to begin.";
  progressText = "";
  sessionSummary?: SessionSummary; // Session summary for detailed display
  showDetailedAnalysis = false; // Toggle for detailed analysis panel
  detailedAnalysisButtonArea?: { x: number, y: number, width: number, height: number }; // Click area for detailed analysis

  // Hidden canvas for frame capture only (kept off-DOM)
  private captureCanvas: HTMLCanvasElement;

  // Animation frame ID for cancellation
  private animationFrameId?: number;

  // Frame rate control
  private lastFrameTime = 0;
  private readonly targetFrameInterval = 1000 / 20; // ~20 FPS

  // Async processing control
  private processingFrame = false;
  private pendingFrame = false;

  // Canvas sizing (logical units = video pixels; backing store uses DPR)
  private logicalW = 0;
  private logicalH = 0;

  // Smoothing (reduces jitter; makes UI feel “premium”)
  private readonly smoothAlpha = 0.35; // higher = snappier, lower = smoother
  private smoothedFace?: Landmark[];
  private smoothedHand?: Landmark[];

  // Minimal throttled debug hook (kept quiet by default)
  private lastDebugAt = 0;
  private readonly debugEveryMs = 2000;

  constructor(
    private cam: CameraService,
    private auth: AuthService,
    private zone: NgZone
  ) {
    this.captureCanvas = document.createElement("canvas");

    // Stop camera if user background-tabs (prevents confusion + saves battery)
    document.addEventListener("visibilitychange", this.onVisibilityChange, { passive: true });
  }

  // Optional convenience getters for template bindings
  get canStart() { return this.uiState === UiState.Idle || this.uiState === UiState.Stopped || this.uiState === UiState.Error; }
  get canStop() { return this.uiState === UiState.Running || this.uiState === UiState.Starting; }
  get canReload() { return this.uiState === UiState.Running; }
  get isBusy() { return this.uiState === UiState.Starting; }

  async start() {
    if (!this.canStart) return;

    this.setState(UiState.Starting, "Starting…", "Warming up camera and session.");
    this.running = true;
    this.error = undefined;
    this.result = undefined;
    this.progressText = "";

    try {
      const videoEl = this.video.nativeElement;

      // Start camera first so user sees immediate feedback
      await this.cam.start(videoEl);

      // Wait for metadata so we know the true dimensions
      await this.ensureVideoMetadata(videoEl);

      // Init backend/session
      await this.auth.initialize(this.backendUrl);
      await this.auth.startAuth();

      // Size canvases (crisp on Retina)
      this.syncCanvasToVideo();

      // Reset smoothing buffers
      this.smoothedFace = undefined;
      this.smoothedHand = undefined;

      this.setState(UiState.Running, "Verifying…", "Follow the on-screen challenge.");
      this.loop();
    } catch (e: any) {
      this.fail(e);
    }
  }

  stop() {
    // Idempotent stop
    this.running = false;

    // Clear transient UI state
    this.error = undefined;
    this.result = undefined;
    this.progressText = "";

    // Cancel animation frame
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = undefined;
    }

    // Stop camera and clear feed
    try { this.cam.stop(); } catch { /* noop */ }
    const videoEl = this.video.nativeElement;
    try { videoEl.srcObject = null; } catch { /* noop */ }

    // Clear overlay
    this.clearOverlay();

    // Disconnect backend
    try { this.auth.disconnect(); } catch { /* noop */ }

    // State update
    this.setState(UiState.Stopped, "Stopped", "Press Start to try again.");
  }

  stopCameraOnly() {
    // Stop processing but preserve authentication results and UI state
    this.running = false;

    // Cancel animation frame
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = undefined;
    }

    // Stop camera and clear feed
    try { this.cam.stop(); } catch { /* noop */ }
    const videoEl = this.video.nativeElement;
    try { videoEl.srcObject = null; } catch { /* noop */ }

    // Clear overlay
    this.clearOverlay();

    // Disconnect backend
    try { this.auth.disconnect(); } catch { /* noop */ }

    // Don't change UI state - preserve success state and session summary
  }

  async reload() {
    if (!this.canReload) return;

    this.error = undefined;
    this.progressText = "";
    this.setState(UiState.Running, "Resetting…", "Starting a new challenge sequence.");

    try {
      this.processingFrame = false;
      this.pendingFrame = false;
      this.result = undefined;

      await this.auth.resetAuth();

      // Kick one immediate frame to make reset feel instant
      if (this.running) {
        const frame = this.cam.capture(this.video.nativeElement, this.captureCanvas, 0.7);
        this.processingFrame = true;
        this.processFrameAsync(frame);
      }
    } catch {
      // Reset failed — silently continue so the camera stays live.
      this.setState(UiState.Running, "Verifying…", "Follow the on-screen challenge.");
    }
  }

  private async loop() {
    if (!this.running) return;

    const now = performance.now();
    const elapsed = now - this.lastFrameTime;

    if (elapsed < this.targetFrameInterval) {
      this.animationFrameId = requestAnimationFrame(() => this.loop());
      return;
    }
    this.lastFrameTime = now;

    try {
      // Capture frame (balanced quality)
      const frame = this.cam.capture(this.video.nativeElement, this.captureCanvas, 0.7);

      if (!this.processingFrame) {
        this.processingFrame = true;
        this.processFrameAsync(frame);
      } else {
        this.pendingFrame = true;
      }
    } catch {
      // Skip this frame on capture error — keep the loop alive.
    }

    this.animationFrameId = requestAnimationFrame(() => this.loop());
  }

  private async processFrameAsync(frame: string) {
    try {
      const result = await this.auth.processFrame(frame);

      this.zone.run(() => {
        this.result = result;
        this.error = undefined;

        // Update friendly header status
        const completed = result.details?.["successful_challenges_count"] || 0;
        const required = result.details?.["required_challenges"] || 3;
        const current = this.formatChallengeName(result.details?.["current_challenge"]);

        this.progressText = `Progress: ${completed}/${required}`;

        if (result.authenticated || completed >= required) {
          this.setState(UiState.Success, "Authorized", "You’re all set.");
          // Store session summary for detailed display
          this.sessionSummary = result.session_summary;
          // Stop the camera and processing when authentication succeeds (preserve success state)
          this.stopCameraOnly();
        } else {
          // If there’s a current challenge, guide the user clearly
          if (current) {
            const done = !!result.details?.["challenge_completed"];
            this.setState(
              UiState.Running,
              done ? "Nice — challenge complete" : "Do this now",
              done ? "Waiting for next prompt…" : current
            );
          } else {
            this.setState(UiState.Running, "Verifying…", "Hold still and face the camera.");
          }
        }

        // Draw overlay
        this.drawVisualIndicators(result);

        // (Optional) quiet debug every N seconds
        this.maybeDebug(result);
      });
    } catch (e: any) {
      // Keep running on transient network / backend errors — show a soft status.
      this.zone.run(() => {
        this.statusTitle = "Connection issue";
        this.statusSubtitle = "Retrying…";
      });
    } finally {
      this.processingFrame = false;

      if (this.pendingFrame && this.running) {
        this.pendingFrame = false;

        const freshFrame = this.cam.capture(this.video.nativeElement, this.captureCanvas, 0.7);
        this.processingFrame = true;
        this.processFrameAsync(freshFrame);
      }
    }
  }

  // =========================
  // Drawing / UX Overlay
  // =========================

  drawVisualIndicators(result: AuthResult) {
    if (!result || !result.details) return;

    const canvasEl = this.canvas.nativeElement;
    const ctx = canvasEl.getContext("2d", { alpha: true });
    if (!ctx) return;

    // Always draw in logical units (video pixels)
    ctx.save();

    // Clear
    ctx.clearRect(0, 0, this.logicalW, this.logicalH);

    // Soft vignette / dim (feels much better than a flat dark rectangle)
    this.drawVignette(ctx, this.logicalW, this.logicalH);

    // Draw landmarks only while verifying — hide them once authorized
    const isAuthed = !!result.authenticated || (result.details?.["successful_challenges_count"] || 0) >= (result.details?.["required_challenges"] || 3);
    if (!isAuthed) {
      ctx.save();
      ctx.setTransform(-1, 0, 0, 1, this.logicalW, 0);

      const face = result.details?.["face_landmarks"] as Landmark[] | undefined;
      const hand = result.details?.["hand_landmarks"] as Landmark[] | undefined;
      const handDetected = !!result.details?.["hand_detected"];

      const smoothFace = this.smoothLandmarks(face, "face");
      const smoothHand = this.smoothLandmarks(hand, "hand");

      if (smoothFace?.length) this.drawFaceLandmarks(ctx, smoothFace);
      if (handDetected && smoothHand?.length) this.drawHandLandmarks(ctx, smoothHand);

      ctx.restore();
    }

    // HUD: auth + progress + challenge
    this.drawHud(ctx, result);

    // Scores (optional panel but styled nicer) - Draw after HUD so it appears on top of success overlay
    const scores = result.details?.["scores"] as Scores | undefined;
    if (scores && Object.keys(scores).length) {
      this.drawMetricsScores(ctx, scores, isAuthed);
    }

    // Detailed analysis panel (draws on top of everything when active)
    if (this.showDetailedAnalysis && this.sessionSummary) {
      this.drawDetailedAnalysis(ctx);
    }

    ctx.restore();
  }

  private drawHud(ctx: CanvasRenderingContext2D, result: AuthResult) {
    const completed = result.details?.["successful_challenges_count"] || 0;
    const required = result.details?.["required_challenges"] || 3;
    const confidencePct = Math.round((result.confidence || 0) * 100);

    const authed = !!result.authenticated || completed >= required;

    // Top-left pill
    const title = authed ? "AUTHORIZED" : "VERIFYING";
    const subtitle = authed ? `Confidence ${confidencePct}%` : `Confidence ${confidencePct}% • ${completed}/${required}`;

    const x = 16;
    const y = 14;
    const padX = 14;
    const padY = 10;
    const r = 14;

    ctx.save();
    ctx.font = "600 14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    const titleW = ctx.measureText(title).width;
    ctx.font = "500 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    const subW = ctx.measureText(subtitle).width;
    const w = Math.max(titleW, subW) + padX * 2;
    const h = 44;

    // Glow - increased opacity for better visibility
    ctx.shadowColor = authed ? "rgba(0, 255, 170, 0.55)" : "rgba(255, 215, 120, 0.45)";
    ctx.shadowBlur = 18;

    // Background
    const grad = ctx.createLinearGradient(x, y, x + w, y + h);
    grad.addColorStop(0, "rgba(0,0,0,0.72)");
    grad.addColorStop(1, "rgba(10,10,18,0.72)");
    ctx.fillStyle = grad;
    this.roundRect(ctx, x, y, w, h, r);
    ctx.fill();

    // Border - increased opacity for better visibility
    ctx.shadowBlur = 0;
    ctx.strokeStyle = authed ? "rgba(0, 255, 200, 0.55)" : "rgba(255, 215, 120, 0.45)";
    ctx.lineWidth = 1;
    this.roundRect(ctx, x, y, w, h, r);
    ctx.stroke();

    // Text
    ctx.textAlign = "left";
    ctx.fillStyle = authed ? "rgba(150, 255, 220, 0.95)" : "rgba(255, 225, 170, 0.95)";
    ctx.font = "700 13px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText(title, x + padX, y + 18);

    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.font = "500 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText(subtitle, x + padX, y + 35);

    ctx.restore();

    // Center success overlay (cleaner than the old full green slab)
    if (authed) {
      this.drawSuccessOverlay(ctx);
      // Don't return here - continue to show progress dots and allow metrics to remain visible
    }

    // Challenge prompt (bottom center) — hidden once authorized
    const challenge = this.formatChallengeName(result.details?.["current_challenge"]);
    if (challenge && !authed) {
      const done = !!result.details?.["challenge_completed"];
      const prompt = done ? "Nice — hold for next prompt…" : challenge;

      ctx.save();
      ctx.font = "700 18px system-ui, -apple-system, Segoe UI, Roboto, Arial";
      const tw = ctx.measureText(prompt).width;

      const bx = (this.logicalW - (tw + 36)) / 2;
      const by = this.logicalH - 70;
      const bw = tw + 36;
      const bh = 44;

      ctx.shadowColor = "rgba(0,0,0,0.35)";
      ctx.shadowBlur = 18;

      ctx.fillStyle = done ? "rgba(0, 140, 90, 0.65)" : "rgba(40, 70, 140, 0.65)";
      this.roundRect(ctx, bx, by, bw, bh, 16);
      ctx.fill();

      ctx.shadowBlur = 0;
      ctx.strokeStyle = "rgba(255,255,255,0.18)";
      ctx.lineWidth = 1;
      this.roundRect(ctx, bx, by, bw, bh, 16);
      ctx.stroke();

      ctx.fillStyle = "rgba(255,255,255,0.95)";
      ctx.textAlign = "center";
      ctx.fillText(prompt, this.logicalW / 2, by + 28);

      ctx.restore();
    }

    // Progress dots (top-right)
    this.drawProgressDots(ctx, completed, required);
  }

  private drawSuccessOverlay(ctx: CanvasRenderingContext2D) {
    const w = this.logicalW;
    const h = this.logicalH;

    ctx.save();

    // Darken + subtle green tint
    ctx.fillStyle = "rgba(0, 0, 0, 0.35)";
    ctx.fillRect(0, 0, w, h);

    const gx = ctx.createRadialGradient(w / 2, h / 2, 20, w / 2, h / 2, Math.min(w, h) * 0.7);
    gx.addColorStop(0, "rgba(0, 190, 120, 0.35)");
    gx.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = gx;
    ctx.fillRect(0, 0, w, h);

    // Enhanced card for session summary
    const cardW = Math.min(580, w * 0.85);
    const cardH = this.sessionSummary ? 280 : 180;
    const x = (w - cardW) / 2;
    const y = (h - cardH) / 2;

    ctx.shadowColor = "rgba(0,0,0,0.45)";
    ctx.shadowBlur = 24;
    ctx.fillStyle = "rgba(8, 14, 12, 0.72)";
    this.roundRect(ctx, x, y, cardW, cardH, 22);
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = "rgba(120, 255, 200, 0.22)";
    ctx.lineWidth = 1;
    this.roundRect(ctx, x, y, cardW, cardH, 22);
    ctx.stroke();

    // Check badge
    const cx = w / 2;
    const cy = y + 50;
    const r = 26;

    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "rgba(0, 170, 110, 1)";
    ctx.lineWidth = 6;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(cx - 12, cy + 0);
    ctx.lineTo(cx - 3, cy + 10);
    ctx.lineTo(cx + 14, cy - 12);
    ctx.stroke();

    // Title
    ctx.fillStyle = "rgba(255,255,255,0.95)";
    ctx.textAlign = "center";
    ctx.font = "800 24px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText("🎯 AUTHORIZED", cx, y + 100);

    // Session summary information
    if (this.sessionSummary) {
      const summary = this.sessionSummary;
      ctx.font = "500 13px system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.fillStyle = "rgba(220, 255, 240, 0.9)";
      
      const authMethod = summary.auth_method === "confidence_threshold" ? "Confidence" : "Challenge Count";
      const confidence = Math.round(summary.final_confidence * 100);
      const threshold = Math.round(summary.auth_threshold * 100);
      
      ctx.fillText(`Authentication Method: ${authMethod}`, cx, y + 130);
      ctx.fillText(`Final Confidence: ${confidence}% (threshold: ${threshold}%)`, cx, y + 150);
      ctx.fillText(`Challenges Completed: ${summary.challenges_completed} of ${summary.challenges_required}`, cx, y + 170);
      ctx.fillText(`Session Duration: ${summary.session_duration.toFixed(1)}s`, cx, y + 190);
      
      // View detailed analysis button
      ctx.font = "600 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.fillStyle = "rgba(120, 255, 200, 0.95)";
      ctx.fillText("[Click for Detailed Analysis]", cx, y + 220);
      
      // Store button area for click detection
      this.detailedAnalysisButtonArea = {
        x: cx - 100,
        y: y + 210,
        width: 200,
        height: 20
      };
    } else {
      ctx.font = "500 14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
      ctx.fillStyle = "rgba(220, 255, 240, 0.85)";
      ctx.fillText("You may proceed.", cx, y + 130);
    }

    ctx.restore();
  }

  private drawDetailedAnalysis(ctx: CanvasRenderingContext2D) {
    if (!this.sessionSummary || !this.showDetailedAnalysis) return;

    const w = this.logicalW;
    const h = this.logicalH;
    const summary = this.sessionSummary;

    ctx.save();

    // Full overlay background
    ctx.fillStyle = "rgba(0, 0, 0, 0.85)";
    ctx.fillRect(0, 0, w, h);

    // Main panel
    const panelW = Math.min(700, w * 0.9);
    const panelH = Math.min(600, h * 0.85);
    const panelX = (w - panelW) / 2;
    const panelY = (h - panelH) / 2;

    // Panel background
    ctx.shadowColor = "rgba(0,0,0,0.6)";
    ctx.shadowBlur = 30;
    ctx.fillStyle = "rgba(12, 20, 16, 0.95)";
    this.roundRect(ctx, panelX, panelY, panelW, panelH, 20);
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = "rgba(120, 255, 200, 0.3)";
    ctx.lineWidth = 2;
    this.roundRect(ctx, panelX, panelY, panelW, panelH, 20);
    ctx.stroke();

    // Title
    ctx.fillStyle = "rgba(120, 255, 200, 1)";
    ctx.textAlign = "center";
    ctx.font = "700 18px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText("🔍 DETAILED AUTHENTICATION ANALYSIS", w / 2, panelY + 35);

    // Close button
    ctx.fillStyle = "rgba(255, 120, 120, 0.8)";
    ctx.font = "600 14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.textAlign = "right";
    ctx.fillText("[Close]", panelX + panelW - 20, panelY + 35);

    let currentY = panelY + 70;
    const leftCol = panelX + 30;
    const rightCol = panelX + panelW / 2 + 20;
    const lineHeight = 22;

    // A. Confidence Breakdown
    ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
    ctx.textAlign = "left";
    ctx.font = "600 14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText("A. CONFIDENCE BREAKDOWN", leftCol, currentY);
    currentY += 25;

    ctx.font = "500 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillStyle = "rgba(220, 255, 240, 0.9)";
    
    const confidence = Math.round(summary.final_confidence * 100);
    const passiveBase = Math.round(summary.passive_base * 100);
    const challengeBoost = Math.round(summary.challenge_boost * 100);
    
    ctx.fillText(`Final Confidence: ${confidence}%`, leftCol, currentY);
    currentY += lineHeight;
    ctx.fillText(`├─ Passive Base: ${passiveBase}% (face detected)`, leftCol, currentY);
    currentY += lineHeight;
    ctx.fillText(`├─ Challenge Boost: ${challengeBoost}% (${summary.challenges_completed} × 18%)`, leftCol, currentY);
    currentY += lineHeight;
    ctx.fillText(`└─ Detector Scores:`, leftCol, currentY);
    currentY += lineHeight;

    // Detector contributions
    for (const [detector, contribution] of Object.entries(summary.detector_contributions)) {
      const contrib = Math.round((contribution as number) * 100);
      const score = Math.round(summary.final_scores[detector] * 100);
      const weight = Math.round(summary.weights[detector.toLowerCase().replace(' ', '_')] * 100);
      ctx.fillText(`   ├─ ${detector}: ${contrib}% (${weight}% × ${score}%)`, leftCol, currentY);
      currentY += lineHeight;
    }

    // B. Challenge History (right column)
    currentY = panelY + 95;
    ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
    ctx.font = "600 14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText("B. CHALLENGE HISTORY", rightCol, currentY);
    currentY += 25;

    ctx.font = "500 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillStyle = "rgba(220, 255, 240, 0.9)";

    if (summary.completed_challenges && summary.completed_challenges.length > 0) {
      summary.completed_challenges.forEach((challenge: any, index: number) => {
        const challengeName = this.formatChallengeName(challenge.challenge);
        const responseTime = challenge.response_time.toFixed(1);
        const score = challenge.score.toFixed(1);
        
        ctx.fillText(`Challenge ${index + 1}: ${challengeName}`, rightCol, currentY);
        currentY += lineHeight;
        ctx.fillText(`├─ Response Time: ${responseTime}s`, rightCol, currentY);
        currentY += lineHeight;
        ctx.fillText(`├─ Score: ${score}/1.0`, rightCol, currentY);
        currentY += lineHeight;
        ctx.fillText(`└─ Contribution: +${Math.round(summary.challenge_boost / summary.challenges_completed * 100)}%`, rightCol, currentY);
        currentY += lineHeight + 5;
      });
    } else {
      ctx.fillText("No challenges completed", rightCol, currentY);
      currentY += lineHeight;
    }

    // C. Authentication Decision (bottom section)
    currentY = panelY + panelH - 120;
    ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
    ctx.font = "600 14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.textAlign = "center";
    ctx.fillText("C. AUTHENTICATION DECISION", w / 2, currentY);
    currentY += 25;

    ctx.font = "500 12px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillStyle = "rgba(120, 255, 200, 0.95)";
    
    if (summary.auth_method === "confidence_threshold") {
      ctx.fillText(`✓ Confidence threshold reached (${confidence}% ≥ ${Math.round(summary.auth_threshold * 100)}%)`, w / 2, currentY);
      currentY += lineHeight;
      ctx.fillStyle = "rgba(220, 255, 240, 0.7)";
      ctx.fillText(`Alternative: Complete ${summary.challenges_required - summary.challenges_completed} more challenges`, w / 2, currentY);
    } else {
      ctx.fillText(`✓ Required challenges completed (${summary.challenges_completed}/${summary.challenges_required})`, w / 2, currentY);
    }

    // D. Session Statistics
    currentY += 30;
    ctx.fillStyle = "rgba(255, 255, 255, 0.95)";
    ctx.font = "600 14px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillText("D. SESSION STATISTICS", w / 2, currentY);
    currentY += 20;

    ctx.font = "500 11px system-ui, -apple-system, Segoe UI, Roboto, Arial";
    ctx.fillStyle = "rgba(220, 255, 240, 0.8)";
    const avgFps = Math.round(summary.frames_processed / summary.session_duration);
    const peakDetector = Object.entries(summary.weights).reduce((a, b) => summary.weights[a[0]] > summary.weights[b[0]] ? a : b)[0];
    
    ctx.fillText(`Frames: ${summary.frames_processed} | Duration: ${summary.session_duration.toFixed(1)}s | Avg FPS: ${avgFps} | Peak Detector: ${peakDetector.replace('_', ' ')} (${Math.round(summary.weights[peakDetector] * 100)}%)`, w / 2, currentY);

    ctx.restore();
  }

  private drawProgressDots(ctx: CanvasRenderingContext2D, completed: number, required: number) {
    ctx.save();

    const r = 6;
    const gap = 16;
    const totalW = required * (2 * r) + (required - 1) * gap;
    const x0 = this.logicalW - totalW - 18;
    const y0 = 28;

    for (let i = 0; i < required; i++) {
      const x = x0 + i * (2 * r + gap);

      // outline
      ctx.beginPath();
      ctx.arc(x, y0, r, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,255,255,0.65)";
      ctx.lineWidth = 1;
      ctx.stroke();

      if (i < completed) {
        ctx.beginPath();
        ctx.arc(x, y0, r - 2, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(120, 255, 200, 0.95)";
        ctx.fill();
      }
    }

    ctx.restore();
  }

  private drawVignette(ctx: CanvasRenderingContext2D, w: number, h: number) {
    // Base dim - increased opacity for better visibility
    ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
    ctx.fillRect(0, 0, w, h);

    // Vignette - increased opacity for better visibility
    const g = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.15, w / 2, h / 2, Math.min(w, h) * 0.7);
    g.addColorStop(0, "rgba(0, 0, 0, 0)");
    g.addColorStop(1, "rgba(0, 0, 0, 0.75)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);
  }

  private clearOverlay() {
    const canvasEl = this.canvas.nativeElement;
    const ctx = canvasEl.getContext("2d", { alpha: true });
    if (!ctx) return;
    ctx.clearRect(0, 0, this.logicalW || canvasEl.width, this.logicalH || canvasEl.height);
  }

  // =========================
  // Landmarks drawing (optimized)
  // =========================

  drawFaceLandmarks(ctx: CanvasRenderingContext2D, landmarks: Landmark[]) {
    if (!landmarks?.length) return;

    const w = this.logicalW;
    const h = this.logicalH;

    // Points
    ctx.fillStyle = "rgba(140, 255, 220, 0.25)";
    ctx.beginPath();
    for (const p of landmarks) {
      const x = p.x * w;
      const y = p.y * h;
      ctx.moveTo(x + 2.2, y);
      ctx.arc(x, y, 2.2, 0, Math.PI * 2);
    }
    ctx.fill();

    // Connections
    ctx.strokeStyle = "rgba(120, 255, 200, 0.18)";
    ctx.lineWidth = 1.0;
    ctx.beginPath();
    for (const [i, j] of FACE_CONNECTIONS) {
      const a = landmarks[i];
      const b = landmarks[j];
      if (!a || !b) continue;
      ctx.moveTo(a.x * w, a.y * h);
      ctx.lineTo(b.x * w, b.y * h);
    }
    ctx.stroke();
  }

  drawHandLandmarks(ctx: CanvasRenderingContext2D, landmarks: Landmark[]) {
    if (!landmarks?.length) return;

    const w = this.logicalW;
    const h = this.logicalH;

    // Points with subtle glow
    ctx.save();
    ctx.shadowBlur = 12;

    for (let i = 0; i < landmarks.length; i++) {
      const p = landmarks[i];
      const x = p.x * w;
      const y = p.y * h;

      let color = "rgba(130, 200, 255, 0.28)";
      if (i <= 4) color = "rgba(255, 120, 120, 0.28)";
      else if (i <= 8) color = "rgba(120, 255, 170, 0.28)";
      else if (i <= 12) color = "rgba(220, 140, 255, 0.28)";
      else if (i <= 16) color = "rgba(255, 240, 140, 0.28)";
      else color = "rgba(140, 255, 255, 0.28)";

    ctx.shadowColor = color.replace("0.28", "0.1");
      ctx.fillStyle = color;

      ctx.beginPath();
      ctx.arc(x, y, 3.8, 0, Math.PI * 2);
      ctx.fill();
    }

    // Connections
    ctx.shadowBlur = 0;
    ctx.lineWidth = 1.4;

    for (const [i, j] of HAND_CONNECTIONS) {
      const a = landmarks[i];
      const b = landmarks[j];
      if (!a || !b) continue;

      // finger-ish coloring
      let color = "rgba(130, 200, 255, 0.22)";
      if (i <= 4 || j <= 4) color = "rgba(255, 120, 120, 0.22)";
      else if (i <= 8 || j <= 8) color = "rgba(120, 255, 170, 0.22)";
      else if (i <= 12 || j <= 12) color = "rgba(220, 140, 255, 0.22)";
      else if (i <= 16 || j <= 16) color = "rgba(255, 240, 140, 0.22)";
      else color = "rgba(140, 255, 255, 0.22)";

      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(a.x * w, a.y * h);
      ctx.lineTo(b.x * w, b.y * h);
      ctx.stroke();
    }

    ctx.restore();
  }

  // Enhanced metrics panel with educational information and responsive sizing
  drawMetricsScores(ctx: CanvasRenderingContext2D, scores: Scores, authed = false) {
    const entries = Object.entries(scores);
    if (!entries.length) return;

    // Sort entries by score (highest first) for better educational value
    const sortedEntries = entries.sort(([, a], [, b]) => b - a);

    // When authorized: compact panel in bottom-left. Otherwise: normal top-left panel.
    const scale = authed
      ? Math.min(this.logicalW / 800, this.logicalH / 600, 1.2) * 0.65
      : Math.min(this.logicalW / 800, this.logicalH / 600, 1.2);
    const rowH = 32 * scale;
    const headerH = 36 * scale;
    const panelW = Math.min(380 * scale, this.logicalW * 0.45);
    const panelH = headerH + sortedEntries.length * rowH + 18 * scale;
    const panelX = authed ? 16 : 16 * scale;
    const panelY = authed ? this.logicalH - panelH - 16 : 78 * scale;

    ctx.save();

    // Enhanced glassy panel with better visibility
    ctx.shadowColor = "rgba(0,0,0,0.45)";
    ctx.shadowBlur = 20;

    ctx.fillStyle = "rgba(0, 0, 0, 0.65)"; // More opaque for better readability over success overlay
    this.roundRect(ctx, panelX, panelY, panelW, panelH, 16);
    ctx.fill();

    ctx.shadowBlur = 0;
    ctx.strokeStyle = "rgba(255,255,255,0.35)";
    ctx.lineWidth = 1;
    this.roundRect(ctx, panelX, panelY, panelW, panelH, 16);
    ctx.stroke();

    // Enhanced title with authentication context and responsive font
    const titleFontSize = Math.max(10, 14 * scale);
    const bodyFontSize = Math.max(9, 12 * scale);
    const padding = 14 * scale;
    
    ctx.font = `700 ${titleFontSize}px system-ui, -apple-system, Segoe UI, Roboto, Arial`;
    ctx.fillStyle = "rgba(108, 255, 214, 0.95)"; // Changed to success color
    ctx.textAlign = "left";
    ctx.fillText("🔍 LIVE BIOMETRIC ANALYSIS", panelX + padding, panelY + 22 * scale);

    // Rows with enhanced styling and responsive fonts
    ctx.font = `500 ${bodyFontSize}px system-ui, -apple-system, Segoe UI, Roboto, Arial`;
    let y = panelY + headerH;

    for (const [name, score] of sortedEntries) {
      const threshold = this.thresholdForMetric(name);
      const pass = score >= threshold;
      const isHighContributor = score >= 0.7; // Highlight high-contributing metrics

      // Enhanced name styling for high contributors with responsive fonts
      ctx.fillStyle = isHighContributor ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.75)";
      ctx.textAlign = "left";
      ctx.font = isHighContributor ? 
        `600 ${bodyFontSize}px system-ui, -apple-system, Segoe UI, Roboto, Arial` : 
        `500 ${bodyFontSize}px system-ui, -apple-system, Segoe UI, Roboto, Arial`;
      
      // Add emoji indicators for better visual recognition
      const emoji = this.getMetricEmoji(name);
      ctx.fillText(`${emoji} ${name}`, panelX + padding, y + 18 * scale);

      // Enhanced value display with percentage
      ctx.textAlign = "right";
      ctx.fillStyle = isHighContributor ? "rgba(255,255,255,0.98)" : "rgba(255,255,255,0.85)";
      ctx.font = `600 ${bodyFontSize}px system-ui, -apple-system, Segoe UI, Roboto, Arial`;
      ctx.fillText(`${(score * 100).toFixed(0)}%`, panelX + panelW - 52 * scale, y + 18 * scale);

      // Enhanced progress bar background
      const barX = panelX + padding;
      const barY = y + 24 * scale;
      const barW = panelW - padding * 2 - 60 * scale;
      const barH = 4 * scale;
      
      ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
      this.roundRect(ctx, barX, barY, barW, barH, 2 * scale);
      ctx.fill();
      
      // Enhanced progress bar fill with gradient
      if (score > 0) {
        const fillW = barW * score;
        const gradient = ctx.createLinearGradient(barX, barY, barX + fillW, barY);
        
        if (pass) {
          gradient.addColorStop(0, "rgba(108, 255, 214, 0.8)");
          gradient.addColorStop(1, "rgba(108, 255, 214, 1.0)");
        } else {
          gradient.addColorStop(0, "rgba(255, 120, 120, 0.8)");
          gradient.addColorStop(1, "rgba(255, 120, 120, 1.0)");
        }
        
        ctx.fillStyle = gradient;
        this.roundRect(ctx, barX, barY, fillW, barH, 2 * scale);
        ctx.fill();
      }

      // Enhanced indicator with glow for high contributors
      if (isHighContributor && pass) {
        ctx.shadowColor = "rgba(108, 255, 214, 0.6)";
        ctx.shadowBlur = 8 * scale;
      }
      
      const indicatorRadius = (pass ? 6 : 5) * scale;
      ctx.beginPath();
      ctx.arc(panelX + panelW - 22 * scale, y + 14 * scale, indicatorRadius, 0, Math.PI * 2);
      
      if (pass) {
        ctx.fillStyle = isHighContributor ? "rgba(108, 255, 214, 1.0)" : "rgba(108, 255, 214, 0.85)";
      } else {
        ctx.fillStyle = "rgba(255, 120, 120, 0.85)";
      }
      ctx.fill();
      
      ctx.shadowBlur = 0;

      y += rowH;
    }

    ctx.restore();
  }

  private thresholdForMetric(name: string): number {
    const n = name.toLowerCase();
    if (n.includes("micro_movement") || n.includes("micro movement")) return 0.5;
    if (n.includes("consistency") || n.includes("3d")) return 0.6;
    if (n.includes("blink")) return 0.5;
    if (n.includes("challenge")) return 0.7;
    if (n.includes("texture")) return 0.5;
    if (n.includes("hand")) return 0.6;
    return 0.5;
  }

  private getMetricEmoji(name: string): string {
    const n = name.toLowerCase();
    if (n.includes("micro") && n.includes("movement")) return "🔄";
    if (n.includes("3d") || n.includes("consistency")) return "📐";
    if (n.includes("blink")) return "👁️";
    if (n.includes("challenge")) return "🎯";
    if (n.includes("texture")) return "🔍";
    if (n.includes("hand")) return "✋";
    return "🤖";
  }

  // =========================
  // Smoothing / helpers
  // =========================

  private smoothLandmarks(input: Landmark[] | undefined, kind: "face" | "hand"): Landmark[] | undefined {
    if (!input?.length) {
      if (kind === "face") this.smoothedFace = undefined;
      else this.smoothedHand = undefined;
      return undefined;
    }

    const prev = kind === "face" ? this.smoothedFace : this.smoothedHand;

    if (!prev || prev.length !== input.length) {
      const cloned = input.map(p => ({ ...p }));
      if (kind === "face") this.smoothedFace = cloned;
      else this.smoothedHand = cloned;
      return cloned;
    }

    const a = this.smoothAlpha;
    for (let i = 0; i < input.length; i++) {
      // Add null/undefined checks for TypeScript strict mode
      if (!prev[i] || !input[i]) continue;
      
      prev[i].x = prev[i].x + a * (input[i].x - prev[i].x);
      prev[i].y = prev[i].y + a * (input[i].y - prev[i].y);
      if (typeof input[i].z === "number" && typeof prev[i].z === "number") {
        // Use non-null assertion operators to satisfy TypeScript strict null checks
        const prevZ = prev[i].z!;
        const inputZ = input[i].z!;
        prev[i].z = prevZ + a * (inputZ - prevZ);
      } else if (typeof input[i].z === "number") {
        prev[i].z = input[i].z;
      }
    }
    return prev;
  }

  formatChallengeName(challenge: string | undefined): string {
    if (!challenge) return "";
    return challenge.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  private roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
    const rr = Math.min(r, w / 2, h / 2);
    ctx.beginPath();
    ctx.moveTo(x + rr, y);
    ctx.arcTo(x + w, y, x + w, y + h, rr);
    ctx.arcTo(x + w, y + h, x, y + h, rr);
    ctx.arcTo(x, y + h, x, y, rr);
    ctx.arcTo(x, y, x + w, y, rr);
    ctx.closePath();
  }

  private maybeDebug(result: AuthResult) {
    // Keep your console usable: one log every N ms max
    const now = performance.now();
    if (now - this.lastDebugAt < this.debugEveryMs) return;
    this.lastDebugAt = now;

    // Comment this out entirely if you want zero logs.
    // console.log("Auth snapshot:", {
    //   authenticated: result.authenticated,
    //   confidence: result.confidence,
    //   challenge: result.details?.["current_challenge"],
    //   completed: result.details?.["successful_challenges_count"],
    //   required: result.details?.["required_challenges"],
    // });
  }

  // =========================
  // Sizing / lifecycle
  // =========================

  private async ensureVideoMetadata(videoEl: HTMLVideoElement) {
    if (videoEl.videoWidth && videoEl.videoHeight) return;

    await new Promise<void>((resolve, reject) => {
      const onLoaded = () => {
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error("Unable to read camera stream metadata."));
      };
      const cleanup = () => {
        videoEl.removeEventListener("loadedmetadata", onLoaded);
        videoEl.removeEventListener("error", onError);
      };

      videoEl.addEventListener("loadedmetadata", onLoaded, { once: true });
      videoEl.addEventListener("error", onError, { once: true });
    });
  }

  private syncCanvasToVideo() {
    const videoEl = this.video.nativeElement;
    const canvasEl = this.canvas.nativeElement;

    const vw = videoEl.videoWidth || canvasEl.width || 640;
    const vh = videoEl.videoHeight || canvasEl.height || 480;

    // Get the actual displayed size from CSS (responsive)
    const rect = canvasEl.getBoundingClientRect();
    const displayW = rect.width;
    const displayH = rect.height;

    // Use display dimensions for logical coordinates to match what user sees
    this.logicalW = displayW;
    this.logicalH = displayH;

    // Backing store scaling for crispness
    const dpr = Math.max(1, Math.min(2.5, window.devicePixelRatio || 1));
    
    // Set canvas backing store to match display size with device pixel ratio
    canvasEl.width = Math.round(displayW * dpr);
    canvasEl.height = Math.round(displayH * dpr);

    // Don't override CSS sizing - let CSS handle responsive layout
    // canvasEl.style.width and canvasEl.style.height removed to fix scaling issues

    const ctx = canvasEl.getContext("2d", { alpha: true });
    if (ctx) {
      // Reset and scale: draw using logical units (video pixels)
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // Capture canvas can stay 1:1 logical
    this.captureCanvas.width = vw;
    this.captureCanvas.height = vh;
  }

  @HostListener("window:resize")
  onResize() {
    if (!this.running) return;
    // If video dimension changes (rare), resync
    this.syncCanvasToVideo();
  }

  @HostListener("click", ["$event"])
  onCanvasClick(event: MouseEvent) {
    if (!this.detailedAnalysisButtonArea || !this.sessionSummary) return;
    
    const canvas = this.canvas.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const scaleX = this.logicalW / rect.width;
    const scaleY = this.logicalH / rect.height;
    
    const clickX = (event.clientX - rect.left) * scaleX;
    const clickY = (event.clientY - rect.top) * scaleY;
    
    const area = this.detailedAnalysisButtonArea;
    if (clickX >= area.x && clickX <= area.x + area.width &&
        clickY >= area.y && clickY <= area.y + area.height) {
      this.showDetailedAnalysis = !this.showDetailedAnalysis;
      // Redraw to show/hide detailed analysis
      if (this.result) {
        this.drawVisualIndicators(this.result);
      }
    }
  }

  private onVisibilityChange = () => {
    // Do not stop automatically — the user must press Stop or complete all challenges.
  };

  private setState(state: UiState, title: string, subtitle: string) {
    this.uiState = state;
    this.statusTitle = title;
    this.statusSubtitle = subtitle;

    // Keep backward-compatible flags
    this.running = state === UiState.Running || state === UiState.Starting || state === UiState.Success;
  }

  private fail(e: any) {
    this.zone.run(() => {
      const message = e?.message || String(e) || "Something went wrong.";
      this.error = message;
      this.setState(UiState.Error, "Error", message);
      this.running = false;
    });

    // Clean up hard to avoid zombie camera/session
    try { this.cam.stop(); } catch { /* noop */ }
    try { this.auth.disconnect(); } catch { /* noop */ }
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = undefined;
    }
    this.clearOverlay();
  }

  // =========================
  // Session Summary Methods
  // =========================

  /**
   * Get detector entries for display in the summary panel
   */
  getDetectorEntries(): Array<{name: string, contribution: number, score: number, weight: number}> {
    if (!this.sessionSummary) return [];
    
    const entries: Array<{name: string, contribution: number, score: number, weight: number}> = [];
    
    // Combine detector contributions with their scores and weights
    Object.keys(this.sessionSummary.detector_contributions).forEach(detectorName => {
      const contribution = this.sessionSummary!.detector_contributions[detectorName];
      const score = this.sessionSummary!.final_scores[detectorName] || 0;
      const weight = this.sessionSummary!.weights[detectorName] || 0;
      
      entries.push({
        name: detectorName,
        contribution: contribution,
        score: score,
        weight: weight
      });
    });
    
    // Sort by contribution (highest first)
    return entries.sort((a, b) => b.contribution - a.contribution);
  }

  /**
   * Get CSS class based on score value
   */
  getScoreClass(score: number): string {
    if (score >= 0.8) return 'score-high';
    if (score >= 0.6) return 'score-medium';
    if (score >= 0.4) return 'score-low';
    return 'score-very-low';
  }

  /**
   * Get human-readable description for each detector type
   */
  getDetectorDescription(detectorName: string): string {
    const name = detectorName.toLowerCase();
    
    if (name.includes('micro') && name.includes('movement')) {
      return 'Analyzes subtle facial movements that indicate natural human behavior';
    }
    if (name.includes('3d') || name.includes('consistency')) {
      return 'Verifies three-dimensional facial structure consistency over time';
    }
    if (name.includes('blink')) {
      return 'Detects natural blinking patterns unique to living humans';
    }
    if (name.includes('challenge')) {
      return 'Measures response to interactive challenges like gestures or expressions';
    }
    if (name.includes('texture')) {
      return 'Analyzes skin texture patterns to detect screens or printed photos';
    }
    if (name.includes('hand')) {
      return 'Detects and analyzes hand gestures and movements';
    }
    
    return 'Advanced biometric analysis for human verification';
  }

  /**
   * Reset the session and start fresh
   */
  resetSession(): void {
    // Clear session summary and result
    this.sessionSummary = undefined;
    this.result = undefined;
    this.error = undefined;
    
    // Reset UI state
    this.setState(UiState.Idle, "Ready", "Press Start to begin.");
    this.progressText = "";
    this.showDetailedAnalysis = false;
    
    // Stop any running processes
    this.stop();
  }

  ngOnDestroy() {
    this.stop();
    document.removeEventListener("visibilitychange", this.onVisibilityChange);

    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = undefined;
    }
  }
}