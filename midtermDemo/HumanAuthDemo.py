#!/usr/bin/env python3
"""
HumanAuth Midterm Demo - Simple Authentication Demo

This is a simplified version of the HumanAuth demo that only implements
the three core challenges:
1. Blink Once
2. Show Peace Sign
3. Show Five Fingers

The UI is designed to resemble the web version while being self-contained.

Author: Jason Dank (2026)
"""

from __future__ import annotations

import os
import time
import argparse
from pathlib import Path

import cv2
import numpy as np

from human_auth import HumanAuth, AuthResult, AUTH_THRESHOLD

class HumanAuthMidtermDemo:
    """
    Simple demo application for the HumanAuth system.
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
        self.running = False

    def run(self):
        """Run the demo application."""
        print("Starting HumanAuth Midterm Demo...")
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
                    self.running = True
                    
            elif self.app_state == "AUTHENTICATING":
                # Process frame with HumanAuth
                result = self.auth.update(frame)

                # Update authentication state
                now = time.time()
                if result.authenticated and not self.authenticated:
                    self.authenticated = True
                    self.auth_time = now
                    self.app_state = "SUCCESS"  # Transition to success state
                    self.running = False
                elif not result.authenticated:
                    self.authenticated = False
                    self.auth_time = None

                if self.authenticated and self.auth_time:
                    self.auth_duration = now - self.auth_time

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
                    self.running = True

            # Display frame
            cv2.imshow("HumanAuth Midterm Demo", ui_frame)

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
                    self.running = True
                elif self.app_state == "WELCOME":
                    self.app_state = "AUTHENTICATING"  # Skip welcome screen
                    self.running = True

        # Clean up
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
        
        print("Authentication reset. Starting new session...")

    def _draw_ui(self, frame, result: AuthResult):
        """Draw the user interface on the frame."""
        h, w = frame.shape[:2]
        
        # Draw authentication status
        self._draw_auth_status(frame, result)
        
        # Draw challenge information
        self._draw_challenge_info(frame, result)

        # Always draw hand and face landmarks
        self.auth.draw_debug(frame, result)

        # Draw help overlay if enabled
        if self.show_help:
            self._draw_help(frame)
        
        # Draw minimal controls hint at the bottom
        controls_text = "h:Help | r:Restart | ESC:Exit"
        cv2.putText(
            frame,
            controls_text,
            (10, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (150, 150, 150),
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
            
        # Draw challenge section
        section_y = 70  # Just below the status banner
        
        # Format challenge name for display
        display_challenge = current_challenge.replace("_", " ").title()
        
        # Draw challenge name with status indicator
        challenge_color = (0, 255, 0) if challenge_completed else (0, 165, 255)
        
        cv2.putText(
            frame,
            display_challenge,
            (20, section_y + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            challenge_color,
            1,
            cv2.LINE_AA,
        )
        
        # Draw progress indicator - dots
        for i in range(required_challenges):
            circle_x = w - 50 - (required_challenges - i - 1) * 20
            circle_y = section_y + 25
            
            # Draw filled circle if challenge is completed, empty otherwise
            if i < successful_challenges:
                cv2.circle(frame, (circle_x, circle_y), 5, (0, 255, 0), -1)
            else:
                cv2.circle(frame, (circle_x, circle_y), 5, (255, 255, 255), 1)

    def _draw_auth_status(self, frame, result: AuthResult):
        """Draw authentication status on the frame."""
        h, w = frame.shape[:2]

        # Draw authentication indicator at the top
        banner_height = 10
        
        # Color based on authentication status
        banner_color = (0, 200, 0) if result.authenticated else (0, 0, 200)
        cv2.rectangle(frame, (0, 0), (w, banner_height), banner_color, -1)

    def _draw_auth_progress(self, frame, result: AuthResult):
        """Draw authentication progress bar on the frame."""
        h, w = frame.shape[:2]

        # Draw progress bar at the bottom
        bar_height = 30
        bar_y = h - bar_height - 30
        bar_width = w - 40
        bar_x = 20

        # Draw background
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
        """Draw the welcome screen with logo."""
        h, w = frame.shape[:2]
        
        # Draw semi-transparent dark overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (20, 20, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Load and display the logo
        logo_path = os.path.join(os.path.dirname(__file__), "HumanAuth.png")
        if os.path.exists(logo_path):
            logo = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)
            if logo is not None:
                # Resize logo to appropriate size (30% of screen width)
                logo_width = int(w * 0.3)
                logo_height = int(logo.shape[0] * (logo_width / logo.shape[1]))
                logo = cv2.resize(logo, (logo_width, logo_height))
                
                # Calculate position to center the logo
                x_offset = (w - logo_width) // 2
                y_offset = (h - logo_height) // 2
                
                # If logo has an alpha channel (RGBA), handle transparency
                if logo.shape[2] == 4:
                    # Create a mask from the alpha channel
                    alpha = logo[:, :, 3] / 255.0
                    # Get BGR channels
                    for c in range(3):
                        # Add the logo to the frame with proper alpha blending
                        frame[y_offset:y_offset+logo_height, x_offset:x_offset+logo_width, c] = \
                            frame[y_offset:y_offset+logo_height, x_offset:x_offset+logo_width, c] * (1 - alpha) + \
                            logo[:, :, c] * alpha
                else:
                    # If no alpha channel, just overlay the logo
                    frame[y_offset:y_offset+logo_height, x_offset:x_offset+logo_width] = logo
        
        # Draw minimal controls at the bottom
        controls_text = "Press any key to start"
        text_size = cv2.getTextSize(controls_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)[0]
        cv2.putText(
            frame,
            controls_text,
            (w // 2 - text_size[0] // 2, h - 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
    
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
        instruction = "Press 'r' to restart"
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
        
    def _draw_help(self, frame):
        """Draw help overlay on the frame."""
        h, w = frame.shape[:2]

        # Draw semi-transparent background
        help_overlay = frame.copy()
        cv2.rectangle(help_overlay, (w // 4, h // 4), (3 * w // 4, 3 * h // 4), (30, 30, 30), -1)
        cv2.addWeighted(help_overlay, 0.7, frame, 0.3, 0, frame)

        # Draw help text
        help_text = [
            "HumanAuth Midterm Demo - Help",
            "",
            "This application demonstrates human authentication",
            "using three challenges:",
            "",
            "1. Blink Once - Close and open your eyes",
            "2. Show Peace Sign - Make a peace sign with your hand",
            "3. Show Five Fingers - Show all five fingers of your hand",
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
    parser = argparse.ArgumentParser(description="HumanAuth Midterm Demo")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--face-model", type=str, default=None, help="Path to face landmarker model")
    parser.add_argument("--hand-model", type=str, default=None, help="Path to hand landmarker model")
    args = parser.parse_args()

    demo = HumanAuthMidtermDemo(
        camera_index=args.camera,
        face_model_path=args.face_model,
        hand_model_path=args.hand_model,
    )
    demo.run()


if __name__ == "__main__":
    main()