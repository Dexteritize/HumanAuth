#!/usr/bin/env python3
"""
Simplified HumanAuth Engine for Midterm Demo

This implements the three core challenges:
1. Blink Once
2. Show Peace Sign
3. Show Five Fingers

Author: Jason Dank (2026)
"""

from __future__ import annotations

import os
import time
import math
import random
from pathlib import Path
from collections import deque
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any

import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python as mp_tasks_python
from mediapipe.tasks.python import vision as mp_tasks_vision

# Constants
AUTH_THRESHOLD = 0.7  # Authentication threshold
BLINK_THRESHOLD = 0.2  # Eye aspect ratio threshold for blink detection
CHALLENGE_TIMEOUT_SEC = 10.0  # Challenge timeout in seconds
CHALLENGE_DELAY_SEC = 1.0  # Delay between challenges

# List of challenges
CHALLENGES = [
    "BLINK_ONCE",
    "SHOW_PEACE_SIGN",
    "SHOW_FIVE_FINGERS"
]

# Face mesh connections for drawing
FACE_CONNECTIONS = [
    # Lips outer
    [61, 146], [146, 91], [91, 181], [181, 84], [84, 17],
    [17, 314], [314, 405], [405, 321], [321, 375], [375, 291],
    [61, 185], [185, 40], [40, 39], [39, 37], [37, 0], [0, 267],
    [267, 269], [269, 270], [270, 409], [409, 291],
    # Eyes
    [33, 7], [7, 163], [163, 144], [144, 145], [145, 153], [153, 154], [154, 155], [155, 133], [133, 173], [173, 157], [157, 158], [158, 159], [159, 160], [160, 161], [161, 246], [246, 33],
    [263, 249], [249, 390], [390, 373], [373, 374], [374, 380], [380, 381], [381, 382], [382, 362], [362, 398], [398, 384], [384, 385], [385, 386], [386, 387], [387, 388], [388, 466], [466, 263],
    # Eyebrows
    [70, 63], [63, 105], [105, 66], [66, 107], [107, 55], [55, 65], [65, 52], [52, 53], [53, 46],
    [300, 293], [293, 334], [334, 296], [296, 336], [336, 285], [285, 295], [295, 282], [282, 283], [283, 276],
    # Nose
    [168, 6], [6, 197], [197, 195], [195, 5], [5, 4], [4, 45], [45, 220], [220, 115], [115, 48],
    [48, 64], [64, 98], [98, 97], [97, 2], [2, 326], [326, 327], [327, 278], [278, 294], [294, 331], [331, 297], [297, 338], [338, 10], [10, 151], [151, 9], [9, 8], [8, 168],
    # Face contour
    [10, 338], [338, 297], [297, 332], [332, 284], [284, 251], [251, 389], [389, 356], [356, 454], [454, 323], [323, 361], [361, 288], [288, 397], [397, 365], [365, 379], [379, 378], [378, 400], [400, 377], [377, 152], [152, 148], [148, 176], [176, 149], [149, 150], [150, 136], [136, 172], [172, 58], [58, 132], [132, 93], [93, 234], [234, 127], [127, 162], [162, 21], [21, 54], [54, 103], [103, 67], [67, 109], [109, 10]
]

# Hand connections for drawing
HAND_CONNECTIONS = [
    # Thumb
    [0, 1], [1, 2], [2, 3], [3, 4],
    # Index finger
    [0, 5], [5, 6], [6, 7], [7, 8],
    # Middle finger
    [0, 9], [9, 10], [10, 11], [11, 12],
    # Ring finger
    [0, 13], [13, 14], [14, 15], [15, 16],
    # Pinky
    [0, 17], [17, 18], [18, 19], [19, 20],
    # Palm
    [0, 5], [5, 9], [9, 13], [13, 17]
]


@dataclass
class AuthResult:
    """Authentication result with details."""
    authenticated: bool
    confidence: float
    message: str
    details: Dict[str, Any]


class HumanAuth:
    """
    Simplified HumanAuth engine that only implements the three core challenges.
    """

    def __init__(self, face_model_path: str = None, hand_model_path: str = None):
        """
        Initialize the HumanAuth engine.

        Args:
            face_model_path: Path to the MediaPipe face landmarker model
            hand_model_path: Path to the MediaPipe hand landmarker model
        """
        # Find models if not provided
        if not face_model_path:
            face_model_path = self._find_face_model()
        if not hand_model_path:
            hand_model_path = self._find_hand_model()

        # Initialize face landmarker
        face_options = mp_tasks_vision.FaceLandmarkerOptions(
            base_options=mp_tasks_python.BaseOptions(model_asset_path=face_model_path),
            running_mode=mp_tasks_vision.RunningMode.VIDEO,
            output_face_blendshapes=True,
            num_faces=1
        )
        self.face_landmarker = mp_tasks_vision.FaceLandmarker.create_from_options(face_options)

        # Initialize hand landmarker
        hand_options = mp_tasks_vision.HandLandmarkerOptions(
            base_options=mp_tasks_python.BaseOptions(model_asset_path=hand_model_path),
            running_mode=mp_tasks_vision.RunningMode.VIDEO,
            num_hands=1
        )
        self.hand_landmarker = mp_tasks_vision.HandLandmarker.create_from_options(hand_options)

        # Initialize state
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.face_history = deque(maxlen=30)  # ~1 second at 30fps
        self.hand_history = deque(maxlen=30)
        self.blink_history = deque(maxlen=90)  # ~3 seconds at 30fps

        # Challenge state
        self.current_challenge = None
        self.challenge_start_time = None
        self.challenge_completed = False
        self.challenge_response_time = None
        self.challenge_success_time = None
        self.next_challenge_time = None
        self.completed_challenges = []
        self.successful_challenges_count = 0
        self.required_challenges = 3  # Number of challenges required for authentication

        # Hand state
        self.last_hand_gesture = "NONE"

        # Issue the first challenge
        self._issue_next_challenge()

    def _find_face_model(self) -> str:
        """Find the face landmarker model."""
        # Check common locations
        locations = [
            "face_landmarker.task",
            os.path.join(os.path.dirname(__file__), "face_landmarker.task"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "humanauth-web/backend/face_landmarker.task"),
        ]
        for loc in locations:
            if os.path.exists(loc):
                return loc
        raise FileNotFoundError("Face landmarker model not found. Please provide the path explicitly.")

    def _find_hand_model(self) -> str:
        """Find the hand landmarker model."""
        # Check common locations
        locations = [
            "hand_landmarker.task",
            os.path.join(os.path.dirname(__file__), "hand_landmarker.task"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "humanauth-web/backend/hand_landmarker.task"),
        ]
        for loc in locations:
            if os.path.exists(loc):
                return loc
        raise FileNotFoundError("Hand landmarker model not found. Please provide the path explicitly.")

    def _calculate_eye_aspect_ratio(self, eye_landmarks) -> float:
        """
        Calculate the eye aspect ratio (EAR) for blink detection.

        Args:
            eye_landmarks: List of landmarks for one eye

        Returns:
            Eye aspect ratio (lower values indicate more closed eyes)
        """
        if not eye_landmarks or len(eye_landmarks) < 6:
            return 1.0

        # Extract 2D coordinates
        points = np.array([[p.x, p.y] for p in eye_landmarks])

        # Calculate horizontal distance (eye width)
        h_dist = np.linalg.norm(points[0] - points[3])

        # Calculate vertical distances
        v_dist1 = np.linalg.norm(points[1] - points[5])
        v_dist2 = np.linalg.norm(points[2] - points[4])

        # Calculate EAR
        ear = (v_dist1 + v_dist2) / (2.0 * h_dist + 1e-6)

        return float(ear)

    def _detect_blink(self, landmarks) -> bool:
        """
        Detect if the user is blinking.

        Args:
            landmarks: Face landmarks

        Returns:
            True if a blink is detected, False otherwise
        """
        if not landmarks:
            return False

        # Extract eye landmarks
        left_eye = [landmarks[i] for i in [33, 160, 158, 133, 153, 144]]
        right_eye = [landmarks[i] for i in [263, 387, 385, 362, 380, 374]]

        # Calculate eye aspect ratios
        left_ear = self._calculate_eye_aspect_ratio(left_eye)
        right_ear = self._calculate_eye_aspect_ratio(right_eye)

        # Average the two eyes
        ear = (left_ear + right_ear) / 2.0

        # Detect blink
        blink_detected = ear < BLINK_THRESHOLD

        # Update blink history
        self.blink_history.append(blink_detected)

        return blink_detected

    def _issue_next_challenge(self, allowed_challenges=None) -> str:
        """
        Issue a new challenge that hasn't been completed yet.

        Args:
            allowed_challenges: Optional list of challenges to consider. If None, all challenges are considered.

        Returns:
            The issued challenge
        """
        # Use specified challenges or all challenges
        challenge_pool = allowed_challenges if allowed_challenges is not None else CHALLENGES

        # If all challenges have been completed, reset the list
        if len(self.completed_challenges) >= len(challenge_pool):
            self.completed_challenges = []

        # Get challenges that haven't been completed yet
        available_challenges = [c for c in challenge_pool if c not in self.completed_challenges]

        # If no challenges are available, use any challenge from the allowed pool
        if not available_challenges:
            available_challenges = challenge_pool

        # Choose a random challenge from available challenges
        challenge = random.choice(available_challenges)
        self.current_challenge = challenge
        self.challenge_start_time = time.time()
        self.challenge_completed = False
        self.challenge_response_time = None
        self.next_challenge_time = None
        return challenge

    def _check_challenge_response(self, landmarks, blendshapes, hand_detected=False, hand_gesture="NONE") -> Tuple[bool, float]:
        """
        Check if the user has completed the current challenge.

        Args:
            landmarks: Face landmarks
            blendshapes: Face blendshapes
            hand_detected: Whether a hand is detected
            hand_gesture: The detected hand gesture

        Returns:
            (completed, response_time) tuple
        """
        if not self.current_challenge:
            return False, 0.0

        now = time.time()
        elapsed = now - self.challenge_start_time

        # Challenge timed out
        if elapsed > CHALLENGE_TIMEOUT_SEC:
            return False, 0.0

        # Check if challenge is completed based on the challenge type
        completed = False

        # Face-based challenges
        if landmarks and blendshapes:
            if self.current_challenge == "BLINK_ONCE":
                # Check for blink
                left_eye = [landmarks[i] for i in [33, 160, 158, 133, 153, 144]]
                ear = self._calculate_eye_aspect_ratio(left_eye)

                # If we detect a blink, complete the challenge immediately
                if ear < BLINK_THRESHOLD:
                    completed = True

        # Hand-based challenges
        if self.current_challenge == "SHOW_PEACE_SIGN" and hand_gesture == "PEACE":
            completed = True
        elif self.current_challenge == "SHOW_FIVE_FINGERS" and hand_gesture == "FIVE_FINGERS":
            completed = True

        if completed and not self.challenge_completed:
            self.challenge_completed = True
            self.challenge_response_time = elapsed
            self.challenge_success_time = time.time()

            # Add to completed challenges if not already in the list
            if self.current_challenge not in self.completed_challenges:
                self.completed_challenges.append(self.current_challenge)

            # Increment successful challenges count
            self.successful_challenges_count += 1

            # Set next challenge time
            self.next_challenge_time = time.time() + CHALLENGE_DELAY_SEC

        return completed, elapsed if completed else 0.0

    def _detect_hand(self, frame_bgr) -> Tuple[bool, List, str]:
        """
        Detect hands in the frame and identify gestures.

        Args:
            frame_bgr: BGR image from camera

        Returns:
            (hand_detected, landmarks, gesture) tuple
        """
        # Convert BGR to RGB for MediaPipe
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Process with MediaPipe for hand detection
        timestamp = int(time.time() * 1000)
        hand_result = self.hand_landmarker.detect_for_video(mp_image, timestamp)

        # No hands detected
        if not hand_result.hand_landmarks or len(hand_result.hand_landmarks) == 0:
            return False, [], "NONE"

        # Get landmarks for the first hand
        landmarks = hand_result.hand_landmarks[0]

        # Detect gestures
        gesture = self._identify_hand_gesture(landmarks)

        # Update hand history
        now = time.time()
        self.hand_history.append((now, landmarks, gesture))
        self.last_hand_gesture = gesture

        return True, landmarks, gesture

    def _identify_hand_gesture(self, landmarks) -> str:
        """
        Identify hand gestures with rotation-robust finger extension checks.

        Args:
            landmarks: Hand landmarks

        Returns:
            Detected gesture
        """
        if not landmarks:
            return "NONE"

        def _dist(a, b):
            return float(np.linalg.norm(a - b))

        wrist = np.array([landmarks[0].x, landmarks[0].y, landmarks[0].z], dtype=np.float32)

        def _extended(tip_i: int, pip_i: int, margin: float = 0.010) -> bool:
            tip = np.array([landmarks[tip_i].x, landmarks[tip_i].y, landmarks[tip_i].z], dtype=np.float32)
            pip = np.array([landmarks[pip_i].x, landmarks[pip_i].y, landmarks[pip_i].z], dtype=np.float32)
            return (_dist(tip, wrist) - _dist(pip, wrist)) > margin

        def _thumb_extended(margin: float = 0.008) -> bool:
            tip = np.array([landmarks[4].x, landmarks[4].y, landmarks[4].z], dtype=np.float32)
            mcp = np.array([landmarks[2].x, landmarks[2].y, landmarks[2].z], dtype=np.float32)
            # Thumb sticks out sideways; require distance gain and some lateral spread.
            return (_dist(tip, wrist) - _dist(mcp, wrist)) > margin and abs(tip[0] - wrist[0]) > 0.03

        thumb = _thumb_extended()
        index = _extended(8, 6)
        middle = _extended(12, 10)
        ring = _extended(16, 14)
        pinky = _extended(20, 18)

        # Peace sign: index + middle extended; ring+pinky not; and visible separation
        idx_tip = np.array([landmarks[8].x, landmarks[8].y], dtype=np.float32)
        mid_tip = np.array([landmarks[12].x, landmarks[12].y], dtype=np.float32)
        sep = float(np.linalg.norm(idx_tip - mid_tip))
        if index and middle and (not ring) and (not pinky) and sep > 0.06:
            return "PEACE"

        # Five fingers: all extended
        if thumb and index and middle and ring and pinky:
            return "FIVE_FINGERS"

        return "HAND"

    def update(self, frame_bgr) -> AuthResult:
        """
        Process a frame and update authentication state.

        Args:
            frame_bgr: BGR image from camera

        Returns:
            AuthResult object with authentication status and details
        """
        # Convert BGR to RGB for MediaPipe
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # Process with MediaPipe for face detection
        timestamp = int(time.time() * 1000)
        detection_result = self.face_landmarker.detect_for_video(mp_image, timestamp)

        # Detect hands
        hand_detected, hand_landmarks, hand_gesture = self._detect_hand(frame_bgr)

        # Initialize result details
        details = {
            "face_detected": False,
            "blink_detected": False,
            "hand_detected": hand_detected,
            "hand_gesture": hand_gesture,
            "current_challenge": self.current_challenge,
            "challenge_completed": self.challenge_completed,
            "successful_challenges_count": self.successful_challenges_count,
            "required_challenges": self.required_challenges,
        }

        # Update frame count and time
        self.frame_count += 1
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now

        # Check if face is detected
        face_detected = len(detection_result.face_landmarks) > 0
        details["face_detected"] = face_detected

        # If no face is detected, return early with minimal processing
        if not face_detected:
            return AuthResult(
                authenticated=False,
                confidence=0.0,
                message="No face detected",
                details=details
            )

        # Get landmarks and blendshapes for the first face
        landmarks = detection_result.face_landmarks[0]
        blendshapes = detection_result.face_blendshapes[0] if detection_result.face_blendshapes else []

        # Update face history
        self.face_history.append((now, landmarks))

        # Detect blink
        blink_detected = self._detect_blink(landmarks)
        details["blink_detected"] = blink_detected

        # Check challenge response
        challenge_completed, response_time = self._check_challenge_response(
            landmarks, blendshapes, hand_detected, hand_gesture
        )
        details["challenge_completed"] = challenge_completed
        details["challenge_response_time"] = response_time

        # Issue next challenge if current one is completed and delay has passed
        if self.challenge_completed and self.next_challenge_time and now >= self.next_challenge_time:
            self._issue_next_challenge()
            details["current_challenge"] = self.current_challenge
            details["challenge_completed"] = self.challenge_completed

        # Calculate challenge response score
        challenge_response_score = min(1.0, self.successful_challenges_count / self.required_challenges)
        details["challenge_response_score"] = challenge_response_score

        # Calculate overall confidence
        confidence = challenge_response_score

        # Determine authentication status
        authenticated = confidence >= AUTH_THRESHOLD and self.successful_challenges_count >= self.required_challenges

        # Create message
        if authenticated:
            message = "Authentication successful"
        elif self.successful_challenges_count < self.required_challenges:
            message = f"Complete {self.required_challenges - self.successful_challenges_count} more challenges"
        else:
            message = "Authentication in progress"

        return AuthResult(
            authenticated=authenticated,
            confidence=confidence,
            message=message,
            details=details
        )

    def _draw_face_landmarks(self, frame, landmarks):
        """
        Draw face landmarks on the frame.

        Args:
            frame: BGR image
            landmarks: Face landmarks
        """
        if not landmarks:
            return

        h, w = frame.shape[:2]
        connections = FACE_CONNECTIONS

        # Draw connections with lighter green color and slightly thicker lines
        for connection in connections:
            start_idx = connection[0]
            end_idx = connection[1]

            start_point = (int(landmarks[start_idx].x * w), int(landmarks[start_idx].y * h))
            end_point = (int(landmarks[end_idx].x * w), int(landmarks[end_idx].y * h))

            # Lighter green color for lines
            cv2.line(frame, start_point, end_point, (0, 255, 0), 2)
            
        # Draw landmark points as small circles
        for i, landmark in enumerate(landmarks):
            x, y = int(landmark.x * w), int(landmark.y * h)
            # Draw small green dots for each landmark
            cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

    def _draw_hand_landmarks(self, frame, landmarks):
        """
        Draw hand landmarks on the frame.

        Args:
            frame: BGR image
            landmarks: Hand landmarks
        """
        if not landmarks:
            return

        h, w = frame.shape[:2]
        connections = HAND_CONNECTIONS

        # Draw connections with color-coding for different fingers
        for connection in connections:
            start_idx = connection[0]
            end_idx = connection[1]

            start_point = (int(landmarks[start_idx].x * w), int(landmarks[start_idx].y * h))
            end_point = (int(landmarks[end_idx].x * w), int(landmarks[end_idx].y * h))

            # Color-code different fingers
            if start_idx <= 4 or end_idx <= 4:  # Thumb
                color = (0, 0, 255)  # Red
            elif start_idx <= 8 or end_idx <= 8:  # Index finger
                color = (0, 255, 0)  # Green
            elif start_idx <= 12 or end_idx <= 12:  # Middle finger
                color = (255, 0, 255)  # Magenta
            elif start_idx <= 16 or end_idx <= 16:  # Ring finger
                color = (255, 255, 0)  # Yellow
            else:  # Pinky
                color = (255, 255, 0)  # Cyan (in BGR format)

            cv2.line(frame, start_point, end_point, color, 3)

        # Draw points with color-coding
        for i, landmark in enumerate(landmarks):
            x, y = int(landmark.x * w), int(landmark.y * h)
            
            # Color-code different fingers
            if i <= 4:  # Thumb
                color = (0, 0, 255)  # Red
            elif i <= 8:  # Index finger
                color = (0, 255, 0)  # Green
            elif i <= 12:  # Middle finger
                color = (255, 0, 255)  # Magenta
            elif i <= 16:  # Ring finger
                color = (255, 255, 0)  # Yellow
            else:  # Pinky
                color = (255, 255, 0)  # Cyan (in BGR format)
                
            cv2.circle(frame, (x, y), 4, color, -1)

    def draw_debug(self, frame, result: AuthResult):
        """
        Draw debug information on the frame.

        Args:
            frame: BGR image
            result: AuthResult object
        """
        # Draw face landmarks if face is detected
        if result.details.get("face_detected", False) and self.face_history:
            _, landmarks = self.face_history[-1]
            self._draw_face_landmarks(frame, landmarks)

        # Draw hand landmarks if hand is detected
        if result.details.get("hand_detected", False) and self.hand_history:
            _, landmarks, _ = self.hand_history[-1]
            self._draw_hand_landmarks(frame, landmarks)

        # Draw challenge information
        h, w = frame.shape[:2]
        challenge = result.details.get("current_challenge", "")
        if challenge:
            # Format challenge name for display
            display_challenge = challenge.replace("_", " ").title()
            
            # Draw challenge text
            cv2.putText(
                frame,
                f"Challenge: {display_challenge}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 165, 255),
                2,
                cv2.LINE_AA,
            )
            
            # Draw completion status
            if result.details.get("challenge_completed", False):
                cv2.putText(
                    frame,
                    "Completed!",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )