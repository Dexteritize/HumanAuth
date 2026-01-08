#!/usr/bin/env python3
"""
HumanAuthDemo - Demonstration of Multi-Modal Human Authentication System

This application showcases the HumanAuth system for liveness detection and human authentication.
It uses multiple detection methods to verify that a user is a real human (not a photo or video):

1. 3D Consistency Checking
2. Temporal Analysis (micro-movements, blinks)
3. Active Challenges (including hand-based challenges)
4. Texture/Frequency Analysis
5. Hand Detection and Gesture Recognition

The application displays:
- Authentication status and confidence
- Current challenge and completion status
- Scores for each detection method
- Blink rate and hand detection information
- Support for hand-only authentication when face is not visible

Author: Jason Dank (2026)
"""

from __future__ import annotations

import os
import time
import argparse
from pathlib import Path
from datetime import datetime

import cv2
import numpy as np

"""This demo is intentionally self-contained.

Place this file next to `human_auth.py` and run:
  python3 HumanAuthDemo.py

If you have the MediaPipe task models, pass them explicitly:
  python3 HumanAuthDemo.py --face-model /path/face_landmarker.task --hand-model /path/hand_landmarker.task
"""

from dataclasses import dataclass
from typing import Optional

from human_auth import HumanAuth, AuthResult, AUTH_THRESHOLD


@dataclass
class LogRow:
    ts: float
    face_present: int
    hand_present: int
    confidence: float
    authenticated: int
    note: str


class CSVLogger:
    """Tiny CSV logger (no external dependencies)."""

    def __init__(self, path: str):
        self.path = path
        self._f = open(path, "w", encoding="utf-8", newline="")
        self._f.write("ts,face_present,hand_present,confidence,authenticated,note\n")
        self._f.flush()

    def log(self, row: LogRow):
        note = (row.note or "").replace("\n", " ").replace("\r", " ")
        self._f.write(
            f"{row.ts:.6f},{row.face_present},{row.hand_present},{row.confidence:.4f},{row.authenticated},\"{note}\"\n"
        )
        self._f.flush()

    def close(self):
        try:
            self._f.close()
        except Exception:
            pass


class HumanAuthDemo:
    """
    Demo application for the HumanAuth system.
    """

    def __init__(self, camera_index: int = 0, face_model_path: str = None, hand_model_path: str = None):
        """
        Initialize the demo application.

        Args:
            camera_index: Index of the camera to use
            face_model_path: Path to the MediaPipe face landmarker model
            hand_model_path: Path to the MediaPipe hand landmarker model
        """
        self.camera_index = camera_index
        self.face_model_path = face_model_path
        self.hand_model_path = hand_model_path

        # Initialize camera
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise ValueError(f"Failed to open camera {camera_index}")

        # Get camera resolution
        self.frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Initialize HumanAuth with both face and hand models
        self.auth = HumanAuth(face_model_path, hand_model_path)

        # Initialize logger
        log_dir = Path(__file__).resolve().parent / "logs"
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"auth_session_{timestamp}.csv"
        self.logger = CSVLogger(str(log_path))

        # Authentication state
        self.authenticated = False
        self.auth_time = None
        self.auth_duration = 0.0
        self.auth_start_time = time.time()
        self.show_restart_button = False
        self.restart_requested = False

        # Application state
        self.app_state = "WELCOME"  # States: WELCOME, AUTHENTICATING, SUCCESS
        self.welcome_screen_shown = False
        self.welcome_start_time = time.time()

        # UI state
        self.show_help = False  # Start with help hidden
        self.show_debug = True

    def run(self):
        """Run the demo application."""
        print("Starting HumanAuth Demo...")
        print("Press 'h' to toggle help overlay")
        print("Press 'd' to toggle debug information")
        print("Press 'r' to restart authentication")
        print("Press 'ESC' to exit")

        while True:
            # Capture frame
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to capture frame")
                break

            # Create a clean frame for UI
            ui_frame = frame.copy()
            
            # Handle different application states
            if self.app_state == "WELCOME":
                self._draw_welcome_screen(ui_frame)
                
                # After 3 seconds, automatically transition to authentication
                if time.time() - self.welcome_start_time > 3.0:
                    self.app_state = "AUTHENTICATING"
                    
            elif self.app_state == "AUTHENTICATING":
                # Process frame with HumanAuth
                result = self.auth.update(frame)

                # Update authentication state
                now = time.time()
                if result.authenticated and not self.authenticated:
                    self.authenticated = True
                    self.auth_time = now
                    self.app_state = "SUCCESS"  # Transition to success state
                elif not result.authenticated:
                    self.authenticated = False
                    self.auth_time = None

                if self.authenticated and self.auth_time:
                    self.auth_duration = now - self.auth_time

                # Log results
                self._log_result(result)

                # Draw visualizations
                self._draw_ui(ui_frame, result)
                
            elif self.app_state == "SUCCESS":
                # Draw success screen with restart button
                self._draw_success_screen(ui_frame)
                
                # Show restart button
                self.show_restart_button = True
                
                # If restart requested, reset the authentication state
                if self.restart_requested:
                    self._reset_authentication()
                    self.restart_requested = False
                    self.app_state = "AUTHENTICATING"

            # Display frame
            cv2.imshow("HumanAuth Demo", ui_frame)

            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            elif key == ord("h"):
                self.show_help = not self.show_help
            elif key == ord("d"):
                self.show_debug = not self.show_debug
            elif key == ord("r"):
                # Restart authentication
                if self.app_state == "SUCCESS":
                    self.restart_requested = True
                elif self.app_state == "AUTHENTICATING":
                    self._reset_authentication()  # Allow restart even during authentication
                elif self.app_state == "WELCOME":
                    self.app_state = "AUTHENTICATING"  # Skip welcome screen

        # Clean up
        self.logger.close()
        self.cap.release()
        cv2.destroyAllWindows()
        
    def _reset_authentication(self):
        """Reset the authentication state to start over."""
        # Reset authentication state
        self.authenticated = False
        self.auth_time = None
        self.auth_duration = 0.0
        self.auth_start_time = time.time()
        self.show_restart_button = False
        
        # Reset welcome screen state
        self.welcome_screen_shown = False
        self.welcome_start_time = time.time()
        
        # Reset HumanAuth state
        self.auth = HumanAuth(self.face_model_path, self.hand_model_path)
        
        # Create a new log file
        log_dir = Path(__file__).resolve().parent / "logs"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"auth_session_{timestamp}.csv"
        self.logger.close()
        self.logger = CSVLogger(str(log_path))
        
        print("Authentication reset. Starting new session...")

    def _log_result(self, result: AuthResult):
        """Log authentication result."""
        self.logger.log(
            LogRow(
                ts=time.time(),
                face_present=int(result.details.get("face_detected", False)),
                hand_present=int(result.details.get("hand_detected", False)),
                confidence=float(result.confidence),
                authenticated=int(bool(result.authenticated)),
                note=result.message,
            )
        )

    def _draw_ui(self, frame, result: AuthResult):
        """Draw the user interface on the frame."""
        h, w = frame.shape[:2]
        
        # Create a semi-transparent overlay for better readability
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 10, 30), -1)
        cv2.addWeighted(overlay, 0.2, frame, 0.8, 0, frame)
        
        # Draw authentication status
        self._draw_auth_status(frame, result)
        
        # Draw challenge information
        self._draw_challenge_info(frame, result)

        # Draw debug information if enabled
        if self.show_debug:
            self.auth.draw_debug(frame, result)

        # Draw help overlay if enabled
        if self.show_help:
            self._draw_help(frame)

        # Draw authentication progress bar
        self._draw_auth_progress(frame, result)
        
        # Draw controls hint at the bottom
        controls_text = "Controls:  'h' - Help  |  'd' - Debug  |  'r' - Restart  |  'ESC' - Exit"
        controls_size = cv2.getTextSize(controls_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.putText(
            frame,
            controls_text,
            (w // 2 - controls_size[0] // 2, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )

    def _draw_challenge_info(self, frame, result: AuthResult):
        """Draw information about the current challenge."""
        h, w = frame.shape[:2]
        
        # Get challenge information from result details
        current_challenge = result.details.get("current_challenge", None)
        challenge_completed = result.details.get("challenge_completed", False)
        successful_challenges = result.details.get("successful_challenges_count", 0)
        required_challenges = result.details.get("required_challenges", 3)
        
        if not current_challenge:
            return
            
        # Draw challenge section background
        section_height = 80
        section_y = 70  # Just below the status banner
        cv2.rectangle(frame, (0, section_y), (w, section_y + section_height), (40, 40, 40), -1)
        
        # Draw section title
        cv2.putText(
            frame,
            "Current Challenge:",
            (20, section_y + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 255),
            1,
            cv2.LINE_AA,
        )
        
        # Draw challenge name with status indicator
        challenge_color = (0, 255, 0) if challenge_completed else (0, 165, 255)
        challenge_status = "✓ COMPLETED" if challenge_completed else "IN PROGRESS"
        
        # Format challenge name for display (replace underscores with spaces, capitalize)
        display_challenge = current_challenge.replace("_", " ").title()
        
        cv2.putText(
            frame,
            f"{display_challenge} - {challenge_status}",
            (20, section_y + 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            challenge_color,
            1,
            cv2.LINE_AA,
        )
        
        # Draw challenge progress (X of Y challenges completed)
        progress_text = f"Progress: {successful_challenges}/{required_challenges} Challenges Completed"
        cv2.putText(
            frame,
            progress_text,
            (w - 300, section_y + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        
        # Draw challenge progress circles
        circle_radius = 8
        circle_spacing = 25
        circle_y = section_y + 60
        circle_x_start = w - 300 + len(progress_text) // 2
        
        for i in range(required_challenges):
            x = circle_x_start + i * circle_spacing
            
            # Draw circle outline
            cv2.circle(frame, (x, circle_y), circle_radius, (255, 255, 255), 1)
            
            # Fill circle if challenge is completed
            if i < successful_challenges:
                cv2.circle(frame, (x, circle_y), circle_radius - 2, (0, 255, 0), -1)

    def _draw_auth_status(self, frame, result: AuthResult):
        """Draw authentication status on the frame."""
        h, w = frame.shape[:2]

        # Draw authentication banner at the top
        banner_height = 60
        
        # Gradient color based on confidence
        if result.authenticated:
            banner_color = (0, 150, 0)  # Green for authenticated
        else:
            # Gradient from red to orange based on confidence
            r = 150
            g = int(150 * result.confidence)
            b = 0
            banner_color = (b, g, r)
            
        cv2.rectangle(frame, (0, 0), (w, banner_height), banner_color, -1)

        # Draw authentication status text
        status_text = "AUTHENTICATED" if result.authenticated else "AUTHENTICATION IN PROGRESS"
        cv2.putText(
            frame,
            status_text,
            (w // 2 - 150, banner_height // 2 + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        # Draw authentication duration if authenticated
        if self.authenticated and self.auth_duration > 0:
            duration_text = f"Duration: {self.auth_duration:.1f}s"
            cv2.putText(
                frame,
                duration_text,
                (w - 200, banner_height // 2 + 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
        
        # Draw confidence percentage on the left
        confidence_text = f"Confidence: {result.confidence * 100:.1f}%"
        cv2.putText(
            frame,
            confidence_text,
            (20, banner_height // 2 + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    def _draw_auth_progress(self, frame, result: AuthResult):
        """Draw authentication progress bar on the frame."""
        h, w = frame.shape[:2]

        # Draw progress bar at the bottom
        bar_height = 30
        bar_y = h - bar_height - 30  # Moved up to make room for controls hint
        bar_width = w - 40
        bar_x = 20

        # Draw background with rounded corners
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (50, 50, 50), -1, cv2.LINE_AA)

        # Draw progress with gradient color
        progress_width = int(bar_width * result.confidence)
        
        # Create gradient color based on confidence
        if result.authenticated:
            progress_color = (0, 255, 0)  # Green for authenticated
        else:
            # Gradient from red to yellow based on confidence
            r = 255
            g = int(255 * result.confidence)
            b = 0
            progress_color = (b, g, r)
            
        if progress_width > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), progress_color, -1, cv2.LINE_AA)

        # Draw threshold line
        threshold_x = bar_x + int(bar_width * float(AUTH_THRESHOLD))
        cv2.line(frame, (threshold_x, bar_y - 5), (threshold_x, bar_y + bar_height + 5), (255, 255, 255), 2)
        
        # Draw threshold label
        cv2.putText(
            frame,
            "Threshold",
            (threshold_x - 30, bar_y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        # Draw text
        cv2.putText(
            frame,
            f"Authentication Confidence: {result.confidence:.2f}",
            (bar_x + 10, bar_y + bar_height // 2 + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    def _draw_welcome_screen(self, frame):
        """Draw the welcome screen with instructions."""
        h, w = frame.shape[:2]
        
        # Draw semi-transparent dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (20, 20, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Draw welcome title
        title = "Welcome to HumanAuth"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 2)[0]
        cv2.putText(
            frame,
            title,
            (w // 2 - title_size[0] // 2, h // 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        
        # Draw subtitle
        subtitle = "Advanced Human Authentication System"
        subtitle_size = cv2.getTextSize(subtitle, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 1)[0]
        cv2.putText(
            frame,
            subtitle,
            (w // 2 - subtitle_size[0] // 2, h // 4 + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (200, 200, 255),
            1,
            cv2.LINE_AA,
        )
        
        # Draw instructions
        instructions = [
            "This system will verify that you are a real human by:",
            "• Analyzing your facial features and movements",
            "• Detecting natural micro-movements",
            "• Presenting challenges for you to complete",
            "",
            "You will need to complete 3 challenges to authenticate.",
            "",
            "Starting authentication in a moment...",
        ]
        
        y = h // 2
        for line in instructions:
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
            cv2.putText(
                frame,
                line,
                (w // 2 - text_size[0] // 2, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            y += 30
            
        # Draw controls at the bottom
        controls = [
            "Controls:  'h' - Help  |  'd' - Debug Info  |  'r' - Restart  |  'ESC' - Exit"
        ]
        
        y = h - 50
        for line in controls:
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
            cv2.putText(
                frame,
                line,
                (w // 2 - text_size[0] // 2, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1,
                cv2.LINE_AA,
            )
            y += 25
    
    def _draw_success_screen(self, frame):
        """Draw the success screen with restart button."""
        h, w = frame.shape[:2]
        
        # Draw semi-transparent green overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 80, 0), -1)
        cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
        
        # Draw success message
        title = "Authentication Successful!"
        title_size = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 1.5, 2)[0]
        cv2.putText(
            frame,
            title,
            (w // 2 - title_size[0] // 2, h // 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        
        # Draw authentication duration
        duration_text = f"Authentication completed in {self.auth_duration:.1f} seconds"
        duration_size = cv2.getTextSize(duration_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 1)[0]
        cv2.putText(
            frame,
            duration_text,
            (w // 2 - duration_size[0] // 2, h // 3 + 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (220, 255, 220),
            1,
            cv2.LINE_AA,
        )
        
        # Draw restart button
        button_width = 200
        button_height = 50
        button_x = w // 2 - button_width // 2
        button_y = h // 2 + 50
        
        # Button background
        cv2.rectangle(
            frame,
            (button_x, button_y),
            (button_x + button_width, button_y + button_height),
            (0, 120, 255),
            -1,
        )
        
        # Button border
        cv2.rectangle(
            frame,
            (button_x, button_y),
            (button_x + button_width, button_y + button_height),
            (255, 255, 255),
            2,
        )
        
        # Button text
        button_text = "Restart Authentication"
        text_size = cv2.getTextSize(button_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
        cv2.putText(
            frame,
            button_text,
            (button_x + button_width // 2 - text_size[0] // 2, button_y + button_height // 2 + 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        
        # Draw instruction
        instruction = "Press 'r' to restart or click the button"
        instruction_size = cv2.getTextSize(instruction, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
        cv2.putText(
            frame,
            instruction,
            (w // 2 - instruction_size[0] // 2, button_y + button_height + 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        
        # Check for mouse click on button (if mouse events are enabled)
        # This would require setting up mouse callback, which is beyond the scope of this example
        
    def _draw_help(self, frame):
        """Draw help overlay on the frame."""
        h, w = frame.shape[:2]

        # Draw semi-transparent background
        help_overlay = frame.copy()
        cv2.rectangle(help_overlay, (w // 4, h // 4), (3 * w // 4, 3 * h // 4), (30, 30, 30), -1)
        cv2.addWeighted(help_overlay, 0.7, frame, 0.3, 0, frame)

        # Draw help text
        help_text = [
            "HumanAuth Demo - Help",
            "",
            "This application demonstrates liveness detection",
            "and human authentication using multiple methods:",
            "",
            "1. 3D Consistency Checking",
            "2. Temporal Analysis (micro-movements, blinks)",
            "3. Active Challenges",
            "4. Texture/Frequency Analysis",
            "",
            "Controls:",
            "  'h' - Toggle this help overlay",
            "  'd' - Toggle debug information",
            "  'r' - Restart authentication",
            "  'ESC' - Exit application",
            "",
            "Press 'h' to close this help",
        ]

        y = h // 4 + 30
        for line in help_text:
            cv2.putText(
                frame,
                line,
                (w // 4 + 20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            y += 25


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="HumanAuth Demo")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--face-model", type=str, default=None, help="Path to face landmarker model")
    parser.add_argument("--hand-model", type=str, default=None, help="Path to hand landmarker model")
    args = parser.parse_args()

    demo = HumanAuthDemo(
        camera_index=args.camera,
        face_model_path=args.face_model,
        hand_model_path=args.hand_model,
    )
    demo.run()


if __name__ == "__main__":
    main()
