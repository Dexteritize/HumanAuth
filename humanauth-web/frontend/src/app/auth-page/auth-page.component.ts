import { Component, ElementRef, ViewChild, OnDestroy } from "@angular/core";
import { CommonModule } from "@angular/common";
import { CameraService } from "../services/camera.service";
import { AuthService, AuthResult } from "../services/auth.service";

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

@Component({
  selector: "app-auth-page",
  standalone: true,
  imports: [CommonModule],
  templateUrl: "./auth-page.component.html",
  styleUrls: ["./auth-page.component.scss"],
})
export class AuthPageComponent implements OnDestroy {
  @ViewChild("video", { static: true }) video!: ElementRef<HTMLVideoElement>;
  @ViewChild("canvas", { static: true }) canvas!: ElementRef<HTMLCanvasElement>;

  backendUrl = "http://localhost:8000";
  running = false;
  result?: AuthResult;
  error?: string;

  // Hidden canvas for frame capture only
  private captureCanvas: HTMLCanvasElement;
  // Animation frame ID for cancellation
  private animationFrameId?: number;

  constructor(private cam: CameraService, private auth: AuthService) {
    // Create a hidden canvas for frame capture to avoid dimension conflicts
    this.captureCanvas = document.createElement('canvas');
    this.captureCanvas.style.display = 'none';
    document.body.appendChild(this.captureCanvas);
  }

  async start() {
    // Reset any previous UI state
    this.error = undefined;
    try {
      await this.cam.start(this.video.nativeElement);
      await this.auth.connect(this.backendUrl);
      await this.auth.startAuth();

      // Initialize the visualization canvas dimensions once
      const videoEl = this.video.nativeElement;
      const canvasEl = this.canvas.nativeElement;

      // Wait for video metadata to load to get correct dimensions
      if (!videoEl.videoWidth) {
        await new Promise<void>(resolve => {
          videoEl.onloadedmetadata = () => resolve();
        });
      }

      // Set canvas dimensions to match video
      canvasEl.width = videoEl.videoWidth;
      canvasEl.height = videoEl.videoHeight;

      this.running = true;
      this.loop();
    } catch (e: any) {
      this.error = e.message;
      this.running = false;
      // Ensure we don't leave hardware/services running on failed start
      try { this.cam.stop(); } catch { /* noop */ }
      try { this.auth.disconnect(); } catch { /* noop */ }
    }
  }

  stop() {
    this.running = false;

    // Clear transient error state when stopping
    this.error = undefined;

    // Cancel any pending animation frame
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = undefined;
    }

    this.cam.stop();
    this.auth.disconnect();
  }

  async loop() {
    // If not running, don't schedule another frame
    if (!this.running) return;

    try {
      // Capture frame using the hidden canvas
      const frame = this.cam.capture(
        this.video.nativeElement,
        this.captureCanvas,
        0.7 // Balance between quality and performance
      );

      this.result = await this.auth.processFrame(frame);

      // Draw visual indicators based on the result
      this.drawVisualIndicators(this.result);
    } catch (e: any) {
      // On any processing error, surface the message and stop the session.
      // This ensures the system does not continue or auto-restart; user must press Start.
      this.error = e?.message || String(e);
      this.running = false;
      // Clean up resources to leave a consistent stopped state
      try { this.cam.stop(); } catch { /* noop */ }
      try { this.auth.disconnect(); } catch { /* noop */ }
      // Cancel any pending animation frame (defensive)
      if (this.animationFrameId) {
        cancelAnimationFrame(this.animationFrameId);
        this.animationFrameId = undefined;
      }
      return;
    }

    // Schedule next frame using requestAnimationFrame for smoother rendering
    this.animationFrameId = requestAnimationFrame(() => this.loop());
  }

  drawVisualIndicators(result: AuthResult) {
    if (!result || !result.details) return;

    const canvas = this.canvas.nativeElement;
    // Use an alpha-enabled context so we can draw overlays
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    // Clear the canvas first
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw a darker, more opaque overlay to dim the video feed (normal orientation)
    ctx.fillStyle = 'rgba(0, 0, 0, 0.72)'; // slightly darker
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw landmarks using a flipped drawing transform so they align with the mirrored video
    ctx.save();
    ctx.setTransform(-1, 0, 0, 1, canvas.width, 0);
    if (result.details['face_landmarks']) {
      this.drawFaceLandmarks(ctx, result.details['face_landmarks']);
    }
    if (result.details['hand_landmarks'] && result.details['hand_detected']) {
      this.drawHandLandmarks(ctx, result.details['hand_landmarks']);
    }
    ctx.restore();

    // Draw authentication status
    // Render auth status on a small opaque pill background for readability (normal orientation)
    ctx.font = '16px Arial';
    const authText = `Auth: ${result.authenticated ? 'Yes' : 'No'} (${Math.round(result.confidence * 100)}%)`;
    const padding = 10;
    const textMetrics = ctx.measureText(authText);
    const boxW = textMetrics.width + padding * 2;
    const boxH = 28;
    const boxX = 10;
    const boxY = 8;

    ctx.save();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.85)'; // more opaque background
    const r = 8;
    ctx.beginPath();
    ctx.moveTo(boxX + r, boxY);
    ctx.arcTo(boxX + boxW, boxY, boxX + boxW, boxY + boxH, r);
    ctx.arcTo(boxX + boxW, boxY + boxH, boxX, boxY + boxH, r);
    ctx.arcTo(boxX, boxY + boxH, boxX, boxY, r);
    ctx.arcTo(boxX, boxY, boxX + boxW, boxY, r);
    ctx.closePath();
    ctx.fill();
    ctx.font = '16px Arial';
    ctx.fillStyle = result.authenticated ? 'rgba(108,255,214,0.95)' : 'rgba(255,214,102,0.95)';
    ctx.fillText(authText, boxX + padding, boxY + 19);
    ctx.restore();

    // Compute challenge progress values early so we can show authorised overlay
    const completedChallenges = result.details['successful_challenges_count'] || 0;
    const requiredChallenges = result.details['required_challenges'] || 3;

    // If all challenges complete, show an authorized screen overlay and stop drawing other UI
    if (completedChallenges >= requiredChallenges) {
      // Draw a full-screen authorized message (normal orientation)
      ctx.save();
      ctx.fillStyle = 'rgba(0, 120, 0, 0.9)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Centered message
      ctx.textAlign = 'center';
      ctx.fillStyle = 'white';
      ctx.font = `${Math.round(canvas.width * 0.06)}px Arial`;
      ctx.fillText('AUTHORIZED HUMAN', canvas.width / 2, canvas.height / 2 - 20);

      // Draw a circular check badge
      const cx = canvas.width / 2;
      const cy = canvas.height / 2 + 50;
      const radius = Math.min(canvas.width, canvas.height) * 0.06;

      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = 'white';
      ctx.fill();

      // Check mark
      ctx.strokeStyle = 'rgba(0, 140, 0, 1)';
      ctx.lineWidth = Math.max(6, radius * 0.2);
      ctx.beginPath();
      ctx.moveTo(cx - radius * 0.5, cy - 0.05 * radius);
      ctx.lineTo(cx - radius * 0.1, cy + radius * 0.35);
      ctx.lineTo(cx + radius * 0.6, cy - radius * 0.45);
      ctx.stroke();

      ctx.restore();
      return;
    }

    // Draw challenge information if available
    if (result.details['current_challenge']) {
      // Draw challenge panel (more opaque)
      const panelTop = 50;
      const panelWidth = canvas.width / 2 - 20;
      const panelHeight = 100;

      ctx.save();
      ctx.shadowColor = 'rgba(0,0,0,0.6)';
      ctx.shadowBlur = 18;
      ctx.fillStyle = 'rgba(30, 30, 60, 0.96)'; // nearly opaque
      ctx.fillRect(10, panelTop, panelWidth, panelHeight);
      ctx.lineWidth = 2;
      ctx.strokeStyle = 'rgba(100, 100, 180, 1)';
      ctx.strokeRect(10, panelTop, panelWidth, panelHeight);
      ctx.restore();

      // Draw challenge title
      ctx.font = '16px Arial';
      ctx.fillStyle = 'rgb(150, 150, 255)';
      ctx.fillText('CURRENT CHALLENGE', 20, panelTop + 20);

      // Draw challenge name
      ctx.font = '18px Arial';
      ctx.fillStyle = result.details['challenge_completed'] ? 'green' : 'orange';
      ctx.fillText(
        result.details['current_challenge'].replace(/_/g, ' '),
        20,
        panelTop + 50
      );

      // Draw challenge progress (we computed totals above)
      ctx.font = '16px Arial';
      ctx.fillStyle = 'white';
      ctx.textAlign = 'right';
      ctx.fillText(`Progress: ${completedChallenges}/${requiredChallenges}`, canvas.width - 20, 30);

      // Draw progress circles on the right
      ctx.textAlign = 'start';
      const circleRadius = 8;
      const circleSpacing = 25;
      const circleY = 50;
      const baseX = canvas.width - 150;

      for (let i = 0; i < requiredChallenges; i++) {
        const circleX = baseX + i * circleSpacing;

        // Draw circle outline
        ctx.beginPath();
        ctx.arc(circleX, circleY, circleRadius, 0, Math.PI * 2);
        ctx.strokeStyle = 'white';
        ctx.stroke();

        // Fill circle if challenge is completed
        if (i < completedChallenges) {
          ctx.beginPath();
          ctx.arc(circleX, circleY, circleRadius - 2, 0, Math.PI * 2);
          ctx.fillStyle = 'green';
          ctx.fill();
        }
      }
    }
  }

  drawFaceLandmarks(ctx: CanvasRenderingContext2D, landmarks: any[]) {
    if (!landmarks || !landmarks.length) return;

    // Draw face landmarks
    for (const point of landmarks) {
      const x = point.x * this.canvas.nativeElement.width;
      const y = point.y * this.canvas.nativeElement.height;

      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, Math.PI * 2);
      // Bright, nearly-opaque points with a soft glow
      ctx.save();
      ctx.fillStyle = 'rgba(0, 255, 0, 0.95)';
      ctx.shadowColor = 'rgba(0, 255, 0, 0.55)';
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.restore();
    }

    // Draw connections between landmarks
    ctx.strokeStyle = 'rgba(0, 255, 0, 0.95)';
    ctx.lineWidth = 2;
    ctx.shadowColor = 'rgba(0, 255, 0, 0.35)';
    ctx.shadowBlur = 8;

    for (const [i, j] of FACE_CONNECTIONS) {
      if (landmarks[i] && landmarks[j]) {
        const x1 = landmarks[i].x * this.canvas.nativeElement.width;
        const y1 = landmarks[i].y * this.canvas.nativeElement.height;
        const x2 = landmarks[j].x * this.canvas.nativeElement.width;
        const y2 = landmarks[j].y * this.canvas.nativeElement.height;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
    // Reset shadow to avoid affecting subsequent draws
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'transparent';
  }

  drawHandLandmarks(ctx: CanvasRenderingContext2D, landmarks: any[]) {
    if (!landmarks || !landmarks.length) return;

    // Draw hand landmarks
    for (let i = 0; i < landmarks.length; i++) {
      const point = landmarks[i];
      const x = point.x * this.canvas.nativeElement.width;
      const y = point.y * this.canvas.nativeElement.height;

      // Different colors for different fingers
      let color;
      if (i <= 4) { // Thumb
        color = 'rgba(255, 0, 0, 0.95)';
      } else if (i <= 8) { // Index finger
        color = 'rgba(0, 255, 0, 0.95)';
      } else if (i <= 12) { // Middle finger
        color = 'rgba(255, 0, 255, 0.95)';
      } else if (i <= 16) { // Ring finger
        color = 'rgba(255, 255, 0, 0.95)';
      } else { // Pinky
        color = 'rgba(0, 255, 255, 0.95)';
      }

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.save();
      ctx.fillStyle = color;
      ctx.shadowColor = color.replace(/0\.95\)$/, '0.5)');
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.restore();
    }

    // Draw connections between landmarks
    ctx.lineWidth = 3;

    for (const [i, j] of HAND_CONNECTIONS) {
      if (landmarks[i] && landmarks[j]) {
        const x1 = landmarks[i].x * this.canvas.nativeElement.width;
        const y1 = landmarks[i].y * this.canvas.nativeElement.height;
        const x2 = landmarks[j].x * this.canvas.nativeElement.width;
        const y2 = landmarks[j].y * this.canvas.nativeElement.height;

        // Different colors for different fingers
        let color;
        if (i <= 4 || j <= 4) { // Thumb
          color = 'rgba(255, 0, 0, 0.95)';
        } else if (i <= 8 || j <= 8) { // Index finger
          color = 'rgba(0, 255, 0, 0.95)';
        } else if (i <= 12 || j <= 12) { // Middle finger
          color = 'rgba(255, 0, 255, 0.95)';
        } else if (i <= 16 || j <= 16) { // Ring finger
          color = 'rgba(255, 255, 0, 0.95)';
        } else { // Pinky
          color = 'rgba(0, 255, 255, 0.95)';
        }

        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
    // Reset any lingering shadow state
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'transparent';
  }

  ngOnDestroy() {
    // Stop all processes
    this.stop();

    // Clean up the capture canvas
    if (this.captureCanvas && this.captureCanvas.parentNode) {
      this.captureCanvas.parentNode.removeChild(this.captureCanvas);
    }

    // Cancel any pending animation frames
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = undefined;
    }
  }
}
