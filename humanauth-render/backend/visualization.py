#!/usr/bin/env python3
"""
HumanAuth Visualization Module

This module contains visualization functions for the HumanAuth system.
It provides methods for drawing face landmarks, hand landmarks, and debug information.

Author: Jason Dank (2026)
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional

# Import AuthResult from auth_types
from auth_types import AuthResult

# Facial landmark connections for visualization
LEFT_EYE = [33, 160, 158, 133, 153, 144, 33]
RIGHT_EYE = [263, 387, 385, 362, 380, 373, 263]
LEFT_EYEBROW = [70, 63, 105, 66, 107]
RIGHT_EYEBROW = [336, 296, 334, 293, 300]
MOUTH_OUTER = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 61]
FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454,
    323, 361, 288, 397, 365, 379, 378, 400, 377,
    152, 148, 176, 149, 150, 136, 172, 58, 132,
    93, 234, 127, 162, 21, 54, 103, 67, 109, 10
]

# Hand landmark connections for visualization
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),        # index
    (0, 9), (9, 10), (10, 11), (11, 12),   # middle
    (0, 13), (13, 14), (14, 15), (15, 16), # ring
    (0, 17), (17, 18), (18, 19), (19, 20), # pinky
    (5, 9), (9, 13), (13, 17)              # palm connections
]

def draw_face_landmarks(frame, landmarks):
    """
    Draw facial landmarks on the frame.
    
    Args:
        frame: BGR image to draw on
        landmarks: Face landmarks from MediaPipe
    """
    if not landmarks:
        return
        
    h, w = frame.shape[:2]
    
    # Draw eyes
    draw_landmark_connections(frame, landmarks, LEFT_EYE, (0, 255, 255), 2)  # Yellow
    draw_landmark_connections(frame, landmarks, RIGHT_EYE, (0, 255, 255), 2)
    
    # Draw eyebrows
    draw_landmark_connections(frame, landmarks, LEFT_EYEBROW, (0, 255, 0), 2)  # Green
    draw_landmark_connections(frame, landmarks, RIGHT_EYEBROW, (0, 255, 0), 2)
    
    # Draw mouth
    draw_landmark_connections(frame, landmarks, MOUTH_OUTER, (0, 0, 255), 2)  # Red
    
    # Draw face oval
    draw_landmark_connections(frame, landmarks, FACE_OVAL, (255, 255, 255), 1)  # White

def draw_landmark_connections(frame, landmarks, connections, color, thickness=1):
    """
    Draw connections between landmarks.
    
    Args:
        frame: BGR image to draw on
        landmarks: Face landmarks from MediaPipe
        connections: List of landmark indices to connect
        color: BGR color tuple
        thickness: Line thickness
    """
    h, w = frame.shape[:2]
    points = []
    
    for idx in connections:
        if idx < len(landmarks):
            lm = landmarks[idx]
            x, y = int(lm.x * w), int(lm.y * h)
            points.append((x, y))
            
    if len(points) < 2:
        return
        
    for i in range(len(points) - 1):
        cv2.line(frame, points[i], points[i + 1], color, thickness, cv2.LINE_AA)

def draw_hand_landmarks(frame, landmarks):
    """
    Draw hand landmarks on the frame.
    
    Args:
        frame: BGR image to draw on
        landmarks: Hand landmarks from MediaPipe
    """
    if not landmarks:
        return
        
    h, w = frame.shape[:2]
    
    # Draw hand connections
    for connection in HAND_CONNECTIONS:
        start_idx, end_idx = connection
        if start_idx < len(landmarks) and end_idx < len(landmarks):
            start_lm = landmarks[start_idx]
            end_lm = landmarks[end_idx]
            
            start_point = (int(start_lm.x * w), int(start_lm.y * h))
            end_point = (int(end_lm.x * w), int(end_lm.y * h))
            
            cv2.line(frame, start_point, end_point, (0, 255, 0), 2, cv2.LINE_AA)
    
    # Draw landmark points
    for i, lm in enumerate(landmarks):
        x, y = int(lm.x * w), int(lm.y * h)
        
        # Different colors for different finger landmarks
        if i == 0:  # Wrist
            color = (255, 0, 0)  # Blue
        elif i <= 4:  # Thumb
            color = (0, 0, 255)  # Red
        elif i <= 8:  # Index finger
            color = (0, 255, 0)  # Green
        elif i <= 12:  # Middle finger
            color = (255, 0, 255)  # Magenta
        elif i <= 16:  # Ring finger
            color = (255, 255, 0)  # Cyan
        else:  # Pinky
            color = (0, 255, 255)  # Yellow
            
        cv2.circle(frame, (x, y), 3, color, -1)

def draw_debug(frame, result: AuthResult, current_landmarks=None, current_hand_landmarks=None):
    """
    Draw debug visualization on the frame.
    
    Args:
        frame: BGR image to draw on
        result: AuthResult from update()
        current_landmarks: Current face landmarks
        current_hand_landmarks: Current hand landmarks
    """
    if frame is None:
        return
        
    h, w = frame.shape[:2]
    
    # Draw landmarks if available
    if current_landmarks is not None:
        draw_face_landmarks(frame, current_landmarks)
        
    if current_hand_landmarks is not None:
        draw_hand_landmarks(frame, current_hand_landmarks)
    
    # Draw authentication status
    auth_status = "AUTHORIZED HUMAN" if result.authenticated else "NOT AUTHENTICATED"
    confidence = result.confidence
    
    # Status background
    status_color = (0, 255, 0) if result.authenticated else (0, 0, 255)  # Green or Red
    cv2.rectangle(frame, (0, 0), (w, 40), status_color, -1)
    
    # Status text
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, f"{auth_status} ({confidence:.2f})", (10, 30), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Get details from result
    details = result.details or {}
    
    # Draw challenge progress indicator (X/3 challenges)
    if "successful_challenges_count" in details and "required_challenges" in details:
        completed = details.get("successful_challenges_count", 0)
        required = details.get("required_challenges", 3)
        
        # Draw progress text
        progress_text = f"Challenges: {completed}/{required}"
        text_size = cv2.getTextSize(progress_text, font, 0.7, 2)[0]
        cv2.putText(
            frame,
            progress_text,
            (w - text_size[0] - 10, 30),
            font,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        
        # Draw progress circles
        circle_radius = 8
        circle_spacing = 25
        start_x = w - (circle_spacing * required) - 10
        circle_y = 60
        
        for i in range(required):
            # Draw circle outline
            cv2.circle(
                frame,
                (start_x + i * circle_spacing, circle_y),
                circle_radius,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            # Fill circle if challenge completed
            if i < completed:
                cv2.circle(
                    frame,
                    (start_x + i * circle_spacing, circle_y),
                    circle_radius - 2,
                    (0, 255, 0),
                    -1,
                    cv2.LINE_AA,
                )
    
    # Draw current challenge if active
    if "current_challenge" in details:
        challenge = details.get("current_challenge")
        challenge_completed = details.get("challenge_completed", False)
        
        if challenge and not challenge_completed:
            # Draw semi-transparent panel background
            panel_img = frame.copy()
            cv2.rectangle(panel_img, (20, h - 200), (w - 20, h - 20), (0, 0, 0), -1)
            cv2.addWeighted(panel_img, 0.7, frame, 0.3, 0, frame)
            
            # Draw panel title
            title = "AUTHENTICATION CHALLENGE"
            cv2.putText(
                frame,
                title,
                (40, h - 160),
                font,
                0.8,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            
            # Draw challenge text
            if challenge == "BLINK":
                instruction = "Please blink your eyes"
            elif challenge == "TURN_HEAD_LEFT":
                instruction = "Please turn your head to the left"
            elif challenge == "TURN_HEAD_RIGHT":
                instruction = "Please turn your head to the right"
            elif challenge == "NOD_UP":
                instruction = "Please nod your head up"
            elif challenge == "NOD_DOWN":
                instruction = "Please nod your head down"
            elif challenge == "SMILE":
                instruction = "Please smile"
            elif challenge == "BLINK_ONCE":
                instruction = "Please blink your eyes once"
            elif challenge == "SHOW_PEACE_SIGN":
                instruction = "Please show a peace sign with your hand"
            elif challenge == "SHOW_THUMBS_UP":
                instruction = "Please show a thumbs up with your hand"
            elif challenge == "SHOW_FIVE_FINGERS":
                instruction = "Please show all five fingers of your hand"
            else:
                instruction = f"Please {challenge.lower().replace('_', ' ')}"
            
            cv2.putText(
                frame,
                instruction,
                (40, h - 120),
                font,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            
            # Draw challenge-specific instructions
            if challenge == "BLINK":
                cv2.putText(
                    frame,
                    "Close and open your eyes naturally",
                    (40, h - 80),
                    font,
                    0.6,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            elif challenge in ["TURN_HEAD_LEFT", "TURN_HEAD_RIGHT"]:
                cv2.putText(
                    frame,
                    "Turn your head about 30 degrees",
                    (40, h - 80),
                    font,
                    0.6,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            elif challenge in ["NOD_UP", "NOD_DOWN"]:
                cv2.putText(
                    frame,
                    "Tilt your head slightly up/down",
                    (40, h - 80),
                    font,
                    0.6,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            elif challenge == "SMILE":
                cv2.putText(
                    frame,
                    "Smile naturally, showing teeth if possible",
                    (40, h - 80),
                    font,
                    0.6,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            elif challenge == "BLINK_ONCE":
                cv2.putText(
                    frame,
                    "Close and open your eyes naturally one time",
                    (40, h - 80),
                    font,
                    0.6,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            elif challenge in ["SHOW_PEACE_SIGN", "SHOW_THUMBS_UP", "SHOW_FIVE_FINGERS"]:
                cv2.putText(
                    frame,
                    "Hold your hand up to the camera",
                    (40, h - 80),
                    font,
                    0.6,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
                
                # Draw hand gesture examples
                example_x = w - 150
                example_y = h - 100
                example_size = 100
                
                # Draw simple hand outline
                cv2.rectangle(frame, (example_x, example_y - example_size), (example_x + example_size, example_y), (50, 50, 50), -1)
                
                # Draw fingers
                if challenge == "SHOW_FIVE_FINGERS":
                    # Draw all five fingers
                    finger_width = 15
                    for i in range(5):
                        finger_x = example_x + 10 + (i * (finger_width + 5))
                        cv2.rectangle(frame, (finger_x, example_y - 90), (finger_x + finger_width, example_y - 20), (200, 200, 200), -1)
                        # Rounded fingertip
                        cv2.circle(frame, (finger_x + finger_width//2, example_y - 90), finger_width//2, (200, 200, 200), -1)
                    # Draw palm
                    cv2.rectangle(frame, (example_x + 10, example_y - 20), (example_x + 90, example_y - 5), (200, 200, 200), -1)
                
                elif challenge == "SHOW_PEACE_SIGN":
                    # Draw peace sign
                    finger_width = 15
                    # Index finger
                    cv2.rectangle(frame, (example_x + 30, example_y - 90), (example_x + 30 + finger_width, example_y - 20), (200, 200, 200), -1)
                    cv2.circle(frame, (example_x + 30 + finger_width//2, example_y - 90), finger_width//2, (200, 200, 200), -1)
                    # Middle finger
                    cv2.rectangle(frame, (example_x + 55, example_y - 90), (example_x + 55 + finger_width, example_y - 20), (200, 200, 200), -1)
                    cv2.circle(frame, (example_x + 55 + finger_width//2, example_y - 90), finger_width//2, (200, 200, 200), -1)
                    # Palm
                    cv2.rectangle(frame, (example_x + 10, example_y - 20), (example_x + 90, example_y - 5), (200, 200, 200), -1)
                
                elif challenge == "SHOW_THUMBS_UP":
                    # Draw thumbs up
                    # Thumb
                    cv2.rectangle(frame, (example_x + 40, example_y - 90), (example_x + 60, example_y - 40), (200, 200, 200), -1)
                    cv2.circle(frame, (example_x + 50, example_y - 90), 10, (200, 200, 200), -1)
                    # Fist
                    cv2.rectangle(frame, (example_x + 30, example_y - 40), (example_x + 70, example_y - 10), (200, 200, 200), -1)
            
            # Draw background rectangle inside the panel
            cv2.rectangle(frame, (40, h - 60), (w - 40, h - 40), (50, 50, 50), -1)
            
            # Draw progress bar if challenge timeout is available
            if "challenge_timeout" in details:
                timeout = details.get("challenge_timeout", 0)
                if timeout > 0:
                    progress = min(1.0, timeout / 5.0)  # Assuming 5 second timeout
                    bar_width = int((w - 80) * progress)
                    cv2.rectangle(frame, (40, h - 60), (40 + bar_width, h - 40), (0, 255, 0), -1)
    
    # Draw detection scores if available
    if "scores" in details:
        scores = details.get("scores", {})
        if scores:
            # Draw semi-transparent panel background
            panel_height = 30 + (len(scores) * 30)
            panel_img = frame.copy()
            cv2.rectangle(panel_img, (20, 50), (300, 50 + panel_height), (0, 0, 0), -1)
            cv2.addWeighted(panel_img, 0.7, frame, 0.3, 0, frame)
            
            # Draw panel title
            cv2.putText(
                frame,
                "DETECTION SCORES",
                (30, 75),
                font,
                0.6,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            
            # Draw scores with pass/fail indicators
            y_pos = 105
            for name, score in scores.items():
                # Format the name for display
                display_name = name.replace("_", " ").title()
                
                # Determine if this score passes its threshold
                threshold = 0.5  # Default threshold
                if "micro_movement" in name.lower():
                    threshold = 0.5
                elif "consistency" in name.lower():
                    threshold = 0.6
                elif "blink" in name.lower():
                    threshold = 0.5
                elif "challenge" in name.lower():
                    threshold = 0.7
                elif "texture" in name.lower():
                    threshold = 0.5
                elif "hand" in name.lower():
                    threshold = 0.6
                
                passes = score >= threshold
                
                # Draw score text
                cv2.putText(
                    frame,
                    f"{display_name}:",
                    (30, y_pos),
                    font,
                    0.5,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
                
                # Draw score value
                cv2.putText(
                    frame,
                    f"{score:.2f}",
                    (200, y_pos),
                    font,
                    0.5,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
                
                # Draw pass/fail indicator
                indicator_color = (0, 255, 0) if passes else (0, 0, 255)  # Green or Red
                cv2.circle(frame, (270, y_pos - 5), 5, indicator_color, -1)
                
                y_pos += 30
    
    # Draw additional debug info if available
    if "debug" in details:
        debug = details.get("debug", {})
        if debug:
            # Draw semi-transparent panel background
            panel_img = frame.copy()
            cv2.rectangle(panel_img, (20, h - 200), (300, h - 20), (0, 0, 0), -1)
            cv2.addWeighted(panel_img, 0.7, frame, 0.3, 0, frame)
            
            # Draw panel title
            cv2.putText(
                frame,
                "DEBUG INFO",
                (30, h - 170),
                font,
                0.6,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            
            # Draw blink rate
            if "blink_rate" in debug:
                blink_rate = debug.get("blink_rate", 0)
                cv2.putText(
                    frame,
                    f"Blink rate: {blink_rate:.1f} blinks/min",
                    (30, h - 140),
                    font,
                    0.5,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )
            
            # Draw hand detection info
            if "hand_detected" in debug:
                hand_detected = debug.get("hand_detected", False)
                hand_status = "Detected" if hand_detected else "Not detected"
                cv2.putText(
                    frame,
                    f"Hand: {hand_status}",
                    (30, h - 110),
                    font,
                    0.5,
                    (200, 200, 200),
                    1,
                    cv2.LINE_AA,
                )