import { Injectable } from "@angular/core";

@Injectable({ providedIn: "root" })
export class CameraService {
  private stream?: MediaStream;

  async start(video: HTMLVideoElement) {
    this.stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640, max: 1280 },
        height: { ideal: 480, max: 720 },
        frameRate: { ideal: 15, max: 30 }
      },
      audio: false,
    });
    video.srcObject = this.stream;
    await video.play();
  }

  stop() {
    this.stream?.getTracks().forEach(t => t.stop());
    this.stream = undefined;
  }

  // Initialize canvas dimensions once
  private initializeCanvas(video: HTMLVideoElement, canvas: HTMLCanvasElement): void {
    // Only set dimensions if they don't match
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
    }
  }

  capture(video: HTMLVideoElement, canvas: HTMLCanvasElement, quality = 0.65): string {
    // Initialize canvas dimensions if needed
    this.initializeCanvas(video, canvas);

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return "";

    // Use a more efficient drawing method
    ctx.globalCompositeOperation = 'copy';
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Optimize image quality vs performance
    const imageType = "image/jpeg";
    const encoderOptions = quality;

    try {
      return canvas.toDataURL(imageType, encoderOptions);
    } catch (e) {
      console.error("Error capturing frame:", e);
      return "";
    }
  }
}
