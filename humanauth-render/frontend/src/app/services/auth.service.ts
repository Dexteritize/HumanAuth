import { Injectable } from "@angular/core";
import { HttpClient, HttpHeaders, HttpErrorResponse } from "@angular/common/http";
import { firstValueFrom } from "rxjs";

export interface AuthResult {
  authenticated: boolean;
  confidence: number;
  message: string;
  details: Record<string, any>;
}

export interface ApiConfig {
  apiKey: string;
  apiUrl: string;
}

@Injectable({ providedIn: "root" })
export class AuthService {
  private apiUrl?: string;
  private apiKey?: string;
  sessionId?: string;

  constructor(private http: HttpClient) {}

  /**
   * Initialize the auth service by fetching API configuration
   * @param backendUrl The URL of the backend server
   */
  async initialize(backendUrl: string): Promise<void> {
    try {
      // Fetch API configuration from the backend
      const config = await firstValueFrom(
        this.http.get<ApiConfig>(`${backendUrl}/api/config`)
      );

      this.apiUrl = config.apiUrl;
      this.apiKey = config.apiKey;

      console.log("Auth service initialized with API URL:", this.apiUrl);
    } catch (error) {
      console.error("Failed to initialize auth service:", error);
      throw new Error("Failed to initialize auth service. Check backend connection.");
    }
  }

  /**
   * Get HTTP headers with API key
   */
  private getHeaders(): HttpHeaders {
    if (!this.apiKey) {
      throw new Error("API key not available. Call initialize() first.");
    }

    return new HttpHeaders({
      'Content-Type': 'application/json',
      'X-API-Key': this.apiKey
    });
  }

  /**
   * Clean up resources
   */
  disconnect() {
    this.sessionId = undefined;
  }

  /**
   * Start a new authentication session
   */
  async startAuth(): Promise<void> {
    if (!this.apiUrl) {
      throw new Error("API URL not available. Call initialize() first.");
    }

    try {
      const response = await firstValueFrom(
        this.http.post<any>(
          `${this.apiUrl}/sessions`,
          {},
          { headers: this.getHeaders() }
        )
      );

      if (response.status !== "success") {
        throw new Error(response.message || "Failed to start authentication session");
      }

      this.sessionId = response.data.session_id;
    } catch (error) {
      console.error("Failed to start auth session:", error);
      throw new Error("Failed to start authentication session");
    }
  }

  /**
   * Reset the current authentication session
   */
  async resetAuth(): Promise<void> {
    if (!this.apiUrl || !this.sessionId) {
      throw new Error("No active session. Call startAuth() first.");
    }

    try {
      const response = await firstValueFrom(
        this.http.post<any>(
          `${this.apiUrl}/sessions/${this.sessionId}/reset`,
          {},
          { headers: this.getHeaders() }
        )
      );

      if (response.status !== "success") {
        throw new Error(response.message || "Failed to reset authentication session");
      }
    } catch (error) {
      console.error("Failed to reset auth session:", error);
      throw new Error("Failed to reset authentication session");
    }
  }

  /**
   * Process a frame in the current authentication session
   * @param frame Base64 encoded image data
   */
  async processFrame(frame: string): Promise<AuthResult> {
    if (!this.apiUrl || !this.sessionId) {
      throw new Error("No active session. Call startAuth() first.");
    }

    try {
      const response = await firstValueFrom(
        this.http.post<any>(
          `${this.apiUrl}/sessions/${this.sessionId}/process`,
          { frame },
          { headers: this.getHeaders() }
        )
      );

      if (response.status !== "success") {
        throw new Error(response.message || "Failed to process frame");
      }

      return response.data;
    } catch (error) {
      console.error("Failed to process frame:", error);

      // Check if this is a rate limit error (HTTP 429)
      if (error instanceof HttpErrorResponse && error.status === 429) {
        console.warn("Rate limit exceeded. The application is sending requests too quickly.");
        throw new Error("Rate limit exceeded. Please wait a moment before continuing.");
      }

      throw new Error("Failed to process frame");
    }
  }

  /**
   * Verify a single frame without maintaining a session
   * @param frame Base64 encoded image data
   */
  async verifyFrame(frame: string): Promise<AuthResult> {
    if (!this.apiUrl) {
      throw new Error("API URL not available. Call initialize() first.");
    }

    try {
      const response = await firstValueFrom(
        this.http.post<any>(
          `${this.apiUrl}/verify`,
          { image: frame },
          { headers: this.getHeaders() }
        )
      );

      if (response.status !== "success") {
        throw new Error(response.message || "Failed to verify frame");
      }

      return response.data;
    } catch (error) {
      console.error("Failed to verify frame:", error);
      throw new Error("Failed to verify frame");
    }
  }
}
