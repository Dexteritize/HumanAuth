import { Injectable } from "@angular/core";
import { io, Socket } from "socket.io-client";

export interface AuthResult {
  authenticated: boolean;
  confidence: number;
  message: string;
  details: Record<string, any>;
}

@Injectable({ providedIn: "root" })
export class AuthService {
  private socket?: Socket;
  sessionId?: string;

  async connect(url: string) {
    this.socket = io(url, { transports: ["websocket"] });
    await new Promise<void>(res => this.socket!.on("connect", () => res()));
  }

  disconnect() {
    this.socket?.disconnect();
    this.socket = undefined;
    this.sessionId = undefined;
  }

  async startAuth() {
    if (!this.socket) throw new Error("Socket not connected");
    const data = await new Promise<any>(res => {
      this.socket!.emit("start_auth");
      this.socket!.once("auth_started", res);
    });
    if (data.status !== "success") throw new Error(data.message);
    this.sessionId = data.session_id;
  }

  async processFrame(frame: string): Promise<AuthResult> {
    if (!this.socket || !this.sessionId) throw new Error("No session");
    const data = await new Promise<any>(res => {
      this.socket!.emit("process_frame", { session_id: this.sessionId, frame });
      this.socket!.once("frame_processed", res);
    });
    if (data.status !== "success") throw new Error(data.message);
    return data.result;
  }
}
