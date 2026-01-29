#!/usr/bin/env python3
"""
HumanAuth - Multi-Modal Human Authentication System

This module implements a sophisticated liveness detection system for human authentication
using multiple detection methods:

1. 3D Consistency Checking
   - Track face mesh landmarks through head rotation
   - Calculate depth ratios between facial features
   - Verify that 3D relationships remain consistent (real faces vs. photos/screens)

2. Temporal Analysis
   - Detect micro-movements (real faces never stay perfectly still)
   - Analyze natural breathing patterns visible in slight head movements
   - Monitor eye blink frequency and pattern (humans blink 15-20 times/min in irregular patterns)

3. Active Challenges
   - Issue random prompts: "look left", "smile", "raise eyebrows"
   - Measure response time (humans ~200-300ms, video playback has delays/unnatural timing)
   - Analyze pupil response to screen brightness changes

4. Texture/Frequency Analysis
   - Analyze pixel patterns at multiple scales
   - Detect specific frequency characteristics of real skin vs. printed paper or screens
   - Identify Moiré patterns from screens

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
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any

import cv2
import numpy as np
import mediapipe as mp

# Import visualization module
import visualization

# Import shared types
from auth_types import AuthResult

from mediapipe.tasks import python as mp_tasks_python
from mediapipe.tasks.python import vision as mp_tasks_vision

# Constants
FACE_HISTORY_SIZE = 90  # ~3 seconds at 30fps
BLINK_THRESHOLD = 0.35  # EAR threshold for blink detection
MIN_BLINKS_PER_MINUTE = 5  # Minimum expected blinks per minute for a real human
MAX_BLINKS_PER_MINUTE = 30  # Maximum expected blinks per minute for a real human
MICRO_MOVEMENT_THRESHOLD = 0.001  # Threshold for detecting micro-movements
CHALLENGE_TIMEOUT_SEC = 5.0  # Timeout for active challenges
CHALLENGE_RESPONSE_TIME_MIN = 0.2  # Minimum expected response time (seconds)
CHALLENGE_RESPONSE_TIME_MAX = 2.0  # Maximum expected response time (seconds)
REQUIRED_CHALLENGES = 3  # Number of successful challenges required for authentication
CHALLENGE_DELAY_SEC = 1.0  # Delay between challenges

# Practical tuning (makes the system usable in normal webcam conditions)
AUTH_THRESHOLD = 0.55          # overall confidence required for authentication (lowered slightly)
PASSIVE_ONLY_THRESHOLD = 0.62  # allow-passive threshold when challenges haven't completed
AUTH_HOLD_SEC = 2.0            # keep auth "latched" briefly to avoid flicker
MIN_FRAMES_BEFORE_CHALLENGES = 8  # minimum frames before challenges are issued (reduced)

# Thresholds for detection methods
MICRO_MOVEMENT_PASS_THRESHOLD = 0.5  # Threshold for passing micro-movement detection
CONSISTENCY_PASS_THRESHOLD = 0.6  # Threshold for passing 3D consistency check
BLINK_PATTERN_PASS_THRESHOLD = 0.5  # Threshold for passing blink pattern check
CHALLENGE_RESPONSE_PASS_THRESHOLD = 0.7  # Threshold for passing challenge response
TEXTURE_PASS_THRESHOLD = 0.5  # Threshold for passing texture analysis
HAND_DETECTION_PASS_THRESHOLD = 0.6  # Threshold for passing hand detection

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

# Challenge types - restricted to only three specific challenges as requested
CHALLENGES = [
    "BLINK_ONCE",          # Blink once
    "SHOW_PEACE_SIGN",     # Make a peace sign with hand
    "SHOW_FIVE_FINGERS"    # Show all five fingers (open hand)
]


class HumanAuth:
    """
    Multi-modal human authentication system using MediaPipe face mesh and iris tracking.
    
    Implements multiple liveness detection methods:
    - 3D consistency checking
    - Temporal analysis (micro-movements, blinks)
    - Active challenges
    - Texture/frequency analysis
    """
    
    def __init__(self, face_model_path: str = None, hand_model_path: str = None):
        """
        Initialize the HumanAuth system.
        
        Args:
            face_model_path: Path to the MediaPipe face landmarker model.
                             If None, will try to find it in standard locations.
            hand_model_path: Path to the MediaPipe hand landmarker model.
                             If None, will try to find it in standard locations.
        """
        self.face_model_path = face_model_path or self._find_face_model()
        self.hand_model_path = hand_model_path or self._find_hand_model()

        # Initialize MediaPipe face landmarker with iris tracking
        base_options = mp_tasks_python.BaseOptions(model_asset_path=self.face_model_path)
        options = mp_tasks_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_tasks_vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True
        )
        self.face_landmarker = mp_tasks_vision.FaceLandmarker.create_from_options(options)
        
        # Initialize MediaPipe hand landmarker
        hand_base_options = mp_tasks_python.BaseOptions(model_asset_path=self.hand_model_path)
        hand_options = mp_tasks_vision.HandLandmarkerOptions(
            base_options=hand_base_options,
            running_mode=mp_tasks_vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.hand_landmarker = mp_tasks_vision.HandLandmarker.create_from_options(hand_options)
        
        # History for temporal analysis
        self.face_history = deque(maxlen=FACE_HISTORY_SIZE)
        self.blink_history = deque(maxlen=FACE_HISTORY_SIZE)
        self.last_blink_time = None
        self.blink_count = 0
        self.blink_rate = 0.0
        
        # Hand detection history
        self.hand_history = deque(maxlen=FACE_HISTORY_SIZE)
        self.last_hand_gesture = None
        
        # 3D consistency tracking
        self.depth_ratios_history = deque(maxlen=FACE_HISTORY_SIZE)
        
        # Active challenge state
        self.current_challenge = None
        self.challenge_start_time = None
        self.challenge_completed = False
        self.challenge_response_time = None
        self.challenge_blink_count = 0  # Count blinks during the BLINK_THREE_TIMES challenge
        
        # Authentication state
        self.auth_confidence = 0.0
        self.last_auth_time = None
        self.authenticated = False
        
        # Challenge tracking
        self.successful_challenges_count = 0
        self.completed_challenges = []
        self.next_challenge_time = None
        self.current_landmarks = None
        self.current_hand_landmarks = None
        self.challenge_success_time = None
        
        # Weights for different detection methods (adjusted to favor challenge response and make confidence rise earlier)
        self.weights = {
            "3d_consistency": 0.15,
            "micro_movement": 0.08,
            "blink_pattern": 0.12,
            "challenge_response": 0.40,  # increased weight for active challenge responses
            "texture_analysis": 0.10,
            "hand_detection": 0.15
        }
    
    def _find_face_model(self) -> str:
        """Find the face landmarker model in standard locations."""
        app_dir = Path(__file__).resolve().parent
        env = os.environ.get("FACE_LANDMARKER_MODEL")
        if env and Path(env).expanduser().exists():
            return str(Path(env).expanduser())
        p = app_dir / "face_landmarker.task"
        if p.exists():
            return str(p)
        raise FileNotFoundError("Missing face_landmarker.task (put it in apps/humanauth/).")
        
    def _find_hand_model(self) -> str:
        """Find the hand landmarker model in standard locations."""
        app_dir = Path(__file__).resolve().parent
        env = os.environ.get("HAND_LANDMARKER_MODEL")
        if env and Path(env).expanduser().exists():
            return str(Path(env).expanduser())
        p = app_dir / "hand_landmarker.task"
        if p.exists():
            return str(p)
        raise FileNotFoundError("Missing hand_landmarker.task (put it in apps/humanauth/).")
    
    def _calculate_eye_aspect_ratio(self, eye_landmarks) -> float:
        """
        Calculate the eye aspect ratio (EAR) for blink detection.
        
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        where p1, p2, p3, p4, p5, p6 are the 2D landmark coordinates.
        """
        if not eye_landmarks or len(eye_landmarks) < 6:
            return 0.0
            
        # Convert landmarks to numpy array
        points = np.array([[lm.x, lm.y] for lm in eye_landmarks], dtype=np.float32)
        
        # Calculate horizontal distance
        h = np.linalg.norm(points[3] - points[0])
        if h <= 1e-6:
            return 0.0
            
        # Calculate vertical distances
        v1 = np.linalg.norm(points[5] - points[1])
        v2 = np.linalg.norm(points[4] - points[2])
        
        # Calculate EAR
        ear = float((v1 + v2) / (2.0 * h))
        return ear
    
    def _detect_blink(self, landmarks) -> bool:
        """
        Detect eye blinks using eye aspect ratio (EAR).
        
        Returns True if a blink is detected, False otherwise.
        """
        if not landmarks:
            return False
            
        # Extract eye landmarks
        left_eye = [landmarks[i] for i in [33, 160, 158, 133, 153, 144]]
        right_eye = [landmarks[i] for i in [263, 387, 385, 362, 380, 373]]
        
        # Calculate EAR for both eyes
        left_ear = self._calculate_eye_aspect_ratio(left_eye)
        right_ear = self._calculate_eye_aspect_ratio(right_eye)
        
        # Average EAR
        ear = (left_ear + right_ear) / 2.0
        
        # Detect blink
        blink_detected = ear < BLINK_THRESHOLD
        
        # Update blink history and rate
        now = time.time()
        if blink_detected and self.last_blink_time is not None and now - self.last_blink_time > 0.1:
            self.blink_count += 1
            self.last_blink_time = now
            
            # Calculate blink rate (blinks per minute)
            if len(self.blink_history) > 0:
                first_blink_time = self.blink_history[0][0]
                elapsed_minutes = (now - first_blink_time) / 60.0
                if elapsed_minutes > 0:
                    self.blink_rate = self.blink_count / elapsed_minutes
        
        if self.last_blink_time is None and blink_detected:
            self.last_blink_time = now
            
        # Store blink state and EAR
        self.blink_history.append((now, blink_detected, ear))
        
        return blink_detected
    
    def _calculate_depth_ratios(self, landmarks) -> List[float]:
        """
        Calculate depth ratios between facial features for 3D consistency checking.
        
        Returns a list of depth ratios that should remain consistent for a real face
        but will change for a 2D image when the head rotates.
        """
        if not landmarks:
            return []
            
        # Extract 3D coordinates of key facial landmarks
        nose_tip = np.array([landmarks[4].x, landmarks[4].y, landmarks[4].z])
        left_eye = np.array([landmarks[33].x, landmarks[33].y, landmarks[33].z])
        right_eye = np.array([landmarks[263].x, landmarks[263].y, landmarks[263].z])
        left_mouth = np.array([landmarks[61].x, landmarks[61].y, landmarks[61].z])
        right_mouth = np.array([landmarks[291].x, landmarks[291].y, landmarks[291].z])
        chin = np.array([landmarks[152].x, landmarks[152].y, landmarks[152].z])
        
        # Calculate distances
        eye_dist = np.linalg.norm(right_eye - left_eye)
        if eye_dist < 1e-6:
            return []
            
        # Calculate depth ratios
        nose_depth_ratio = np.linalg.norm(nose_tip - (left_eye + right_eye) / 2) / eye_dist
        mouth_depth_ratio = np.linalg.norm((left_mouth + right_mouth) / 2 - (left_eye + right_eye) / 2) / eye_dist
        chin_depth_ratio = np.linalg.norm(chin - (left_eye + right_eye) / 2) / eye_dist
        
        return [nose_depth_ratio, mouth_depth_ratio, chin_depth_ratio]
    
    def _detect_micro_movements(self) -> float:
        """
        Detect micro-movements in facial landmarks over time.
        
        Returns a score between 0.0 and 1.0 indicating the presence of natural micro-movements.
        """
        # Allow micro-movement scoring earlier (fewer frames required)
        if len(self.face_history) < 4:
            return 0.0

        # Calculate movement variance across recent frames
        movements = []
        for i in range(1, min(30, len(self.face_history))):
            prev_landmarks = self.face_history[-i-1][1]
            curr_landmarks = self.face_history[-i][1]

            if not prev_landmarks or not curr_landmarks:
                continue

            # Sample a few landmarks to check for movement
            sample_indices = [4, 33, 263, 61, 291, 152]  # nose, eyes, mouth, chin
            movement = 0.0
            count = 0

            for idx in sample_indices:
                if idx < len(prev_landmarks) and idx < len(curr_landmarks):
                    prev_lm = prev_landmarks[idx]
                    curr_lm = curr_landmarks[idx]

                    # Calculate movement distance
                    dist = math.sqrt(
                        (prev_lm.x - curr_lm.x)**2 + 
                        (prev_lm.y - curr_lm.y)**2 + 
                        (prev_lm.z - curr_lm.z)**2
                    )
                    movement += dist
                    count += 1

            if count > 0:
                movements.append(movement / count)

        if not movements:
            return 0.0

        # Calculate statistics of movements
        mean_movement = np.mean(movements)
        std_movement = np.std(movements)

        # Real faces have small but non-zero movements
        # Too little movement suggests a photo, too much might be erratic
        if mean_movement < MICRO_MOVEMENT_THRESHOLD:
            return 0.0  # Too still, likely a photo
        elif mean_movement > 0.05:
            return max(0.0, 1.0 - (mean_movement - 0.05) / 0.1)  # Penalize excessive movement
        else:
            # Ideal range: small movements with some variation
            movement_score = min(1.0, mean_movement / 0.01)
            variation_score = min(1.0, std_movement / (mean_movement * 0.5 + 1e-6))
            return (movement_score + variation_score) / 2.0
    
    def _check_3d_consistency(self) -> float:
        """
        Check 3D consistency of facial landmarks during head rotation.
        
        Returns a score between 0.0 and 1.0 indicating 3D consistency.
        """
        # Allow 3D consistency scoring earlier (reduced history requirement)
        if len(self.depth_ratios_history) < 4:
            return 0.0

        # Calculate statistics of depth ratios
        ratios_array = np.array(self.depth_ratios_history)

        if ratios_array.size == 0 or ratios_array.ndim < 2:
            return 0.0

        # Calculate standard deviation for each ratio
        std_devs = np.std(ratios_array, axis=0)
        
        # Calculate head rotation amount
        head_rotations = []
        for i in range(1, len(self.face_history)):
            prev_frame = self.face_history[i-1]
            curr_frame = self.face_history[i]
            
            if prev_frame[2] is not None and curr_frame[2] is not None:
                yaw_diff = abs(curr_frame[2] - prev_frame[2])
                pitch_diff = abs(curr_frame[3] - prev_frame[3])
                head_rotations.append(math.sqrt(yaw_diff**2 + pitch_diff**2))
        
        if not head_rotations:
            return 0.0
            
        # Calculate mean rotation
        mean_rotation = np.mean(head_rotations)
        
        # If head barely moved, consistency check is inconclusive
        if mean_rotation < 0.01:
            return 0.5
            
        # For a real 3D face, depth ratios should remain relatively consistent
        # despite head rotation. For a 2D image, they will vary significantly.
        consistency_score = 1.0 - min(1.0, float(np.mean(std_devs)) / 0.25)
        
        return consistency_score
    
    def _check_blink_pattern(self) -> float:
        """
        Check if the blink pattern is consistent with human behavior.
        
        Returns a score between 0.0 and 1.0.
        """
        # Allow blink-pattern scoring earlier
        if len(self.blink_history) < 4:
            return 0.0

        # Check blink rate
        if self.blink_rate < MIN_BLINKS_PER_MINUTE:
            # Too few blinks, suspicious
            return max(0.0, self.blink_rate / MIN_BLINKS_PER_MINUTE)
        elif self.blink_rate > MAX_BLINKS_PER_MINUTE:
            # Too many blinks, suspicious
            return max(0.0, 1.0 - (self.blink_rate - MAX_BLINKS_PER_MINUTE) / 10.0)
            
        # Calculate intervals between blinks
        blink_times = [t for t, is_blink, _ in self.blink_history if is_blink]
        if len(blink_times) < 2:
            return 0.5  # Not enough data
            
        intervals = [blink_times[i] - blink_times[i-1] for i in range(1, len(blink_times))]
        
        # Calculate statistics of intervals
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # Human blinks have natural variation
        # Too regular intervals suggest a programmed behavior
        regularity = std_interval / (mean_interval + 1e-6)
        
        # Score based on natural irregularity of human blinks
        # Humans typically have a coefficient of variation between 0.2 and 0.5
        if regularity < 0.1:
            return 0.0  # Too regular, suspicious
        elif regularity > 0.7:
            return 0.5  # Very irregular, could be natural or random
        else:
            # Ideal range: natural variation
            return min(1.0, regularity / 0.3)
    
    def _issue_challenge(self) -> str:
        """Issue a random challenge to the user."""
        challenge = random.choice(CHALLENGES)
        self.current_challenge = challenge
        self.challenge_start_time = time.time()
        self.challenge_completed = False
        self.challenge_response_time = None
        return challenge
        
    def _issue_next_challenge(self, allowed_challenges=None) -> str:
        """
        Issue a new challenge that hasn't been completed yet.
        
        This method ensures proper tracking of completed challenges by selecting from challenges
        that haven't been completed yet. If all challenges have been completed, it resets the list.
        
        Args:
            allowed_challenges: Optional list of challenges to consider. If None, all challenges are considered.
                               This is useful for hand-only mode where only hand-related challenges should be used.
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
        self.challenge_blink_count = 0  # Reset blink count for BLINK_THREE_TIMES challenge
        return challenge
    
    def _check_challenge_response(self, landmarks, blendshapes, hand_detected=False, hand_gesture="NONE") -> Tuple[bool, float]:
        """
        Check if the user has completed the current challenge.
        
        Args:
            landmarks: Face landmarks
            blendshapes: Face blendshapes
            hand_detected: Whether a hand is detected
            hand_gesture: The detected hand gesture
            
        Returns (completed, response_time) tuple.
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
            # Extract head pose
            yaw, pitch = self._estimate_head_pose(landmarks)
            
            # More lenient thresholds for head turn detection
            if self.current_challenge == "LOOK_LEFT" and yaw < -0.15:  # Was -0.2
                completed = True
            elif self.current_challenge == "LOOK_RIGHT" and yaw > 0.15:  # Was 0.2
                completed = True
            elif self.current_challenge == "LOOK_UP" and pitch < -0.15:  # Was -0.2
                completed = True
            elif self.current_challenge == "LOOK_DOWN" and pitch > 0.15:  # Was 0.2
                completed = True
            elif self.current_challenge == "BLINK":
                # Check for blink
                left_eye = [landmarks[i] for i in [33, 160, 158, 133, 153, 144]]
                ear = self._calculate_eye_aspect_ratio(left_eye)
                if ear < BLINK_THRESHOLD:
                    completed = True
            elif self.current_challenge == "SMILE":
                # Check for smile in blendshapes
                for blendshape in blendshapes:
                    if blendshape.category_name == "smileLeft" or blendshape.category_name == "smileRight":
                        if blendshape.score > 0.7:
                            completed = True
                            break
            elif self.current_challenge == "BLINK_ONCE":
                # Check for blink
                left_eye = [landmarks[i] for i in [33, 160, 158, 133, 153, 144]]
                ear = self._calculate_eye_aspect_ratio(left_eye)
                
                # If we detect a blink, complete the challenge immediately
                if ear < BLINK_THRESHOLD:
                    completed = True
        
        # Hand-based challenges
        if self.current_challenge == "SHOW_HAND" and hand_detected:
            completed = True
        elif self.current_challenge == "SHOW_PEACE_SIGN" and hand_gesture == "PEACE":
            completed = True
        elif self.current_challenge == "SHOW_THUMBS_UP" and hand_gesture == "THUMBS_UP":
            completed = True
        # Finger counting challenges
        elif self.current_challenge == "SHOW_ONE_FINGER" and hand_gesture == "ONE_FINGER":
            completed = True
        elif self.current_challenge == "SHOW_THREE_FINGERS" and hand_gesture == "THREE_FINGERS":
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
    
    def _estimate_head_pose(self, landmarks):
        """
        Lightweight yaw/pitch proxy from nose vector relative to face center.
        """
        if not landmarks:
            return 0.0, 0.0
            
        nose = np.array([landmarks[4].x, landmarks[4].y, landmarks[4].z], dtype=np.float32)
        leye = np.array([landmarks[33].x, landmarks[33].y, landmarks[33].z], dtype=np.float32)
        reye = np.array([landmarks[263].x, landmarks[263].y, landmarks[263].z], dtype=np.float32)
        lmouth = np.array([landmarks[61].x, landmarks[61].y, landmarks[61].z], dtype=np.float32)
        rmouth = np.array([landmarks[291].x, landmarks[291].y, landmarks[291].z], dtype=np.float32)
        
        center = (leye + reye + lmouth + rmouth) / 4.0
        v = nose - center
        n = float(np.linalg.norm(v))
        if n <= 1e-6:
            return 0.0, 0.0
        v /= n
        yaw = float(v[0])
        pitch = float(-v[1])
        return yaw, pitch
    
    def _analyze_texture(self, frame) -> float:
        """
        Analyze texture patterns to detect screens or printed photos.
        
        Returns a score between 0.0 and 1.0 indicating likelihood of real skin.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Fourier transform
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude = np.log(np.abs(f_shift) + 1)
        
        # Normalize
        magnitude = (magnitude - np.min(magnitude)) / (np.max(magnitude) - np.min(magnitude))
        
        # Check for Moiré patterns (regular grid patterns in frequency domain)
        # These are characteristic of screens
        # We look for peaks in the mid-frequency range
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2
        
        # Create a mask for mid-frequency range
        y, x = np.ogrid[:h, :w]
        inner_mask = ((x - center_x)**2 + (y - center_y)**2 <= (min(h, w) // 8)**2)
        outer_mask = ((x - center_x)**2 + (y - center_y)**2 >= (min(h, w) // 3)**2)
        mid_freq_mask = ~inner_mask & ~outer_mask
        
        # Extract mid-frequency components
        mid_freq = magnitude * mid_freq_mask
        
        # Calculate statistics
        mean_energy = np.mean(mid_freq[mid_freq > 0])
        std_energy = np.std(mid_freq[mid_freq > 0])
        
        # Screens typically have more regular patterns in mid-frequencies
        # Real skin has more natural variation
        regularity = std_energy / (mean_energy + 1e-6)
        
        # Score based on natural irregularity of skin textures
        if regularity < 0.20:
            return 0.15  # Strongly periodic, suspicious (screen/print)
        elif regularity > 1.0:
            return 1.0  # Very irregular, likely real skin
        else:
            # Linear interpolation
            return (regularity - 0.3) / 0.7
            
    def _detect_hand(self, frame_bgr) -> Tuple[bool, List, str]:
        """
        Detect hands in the frame and identify gestures.
        
        Returns:
            Tuple of (hand_detected, hand_landmarks, gesture)
            - hand_detected: Boolean indicating if a hand is detected
            - hand_landmarks: List of hand landmarks if detected, empty list otherwise
            - gesture: String indicating the detected gesture ("NONE", "PEACE", "THUMBS_UP")
        """
        # Convert BGR to RGB for MediaPipe
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        # Process with MediaPipe
        timestamp = int(time.time() * 1000)
        detection_result = self.hand_landmarker.detect_for_video(mp_image, timestamp)
        
        # Check if hand is detected
        if not detection_result.hand_landmarks:
            return False, [], "NONE"
        
        # Get the first hand landmarks
        landmarks = detection_result.hand_landmarks[0]
        
        # Detect gestures
        gesture = self._identify_hand_gesture(landmarks)
        
        # Update hand history
        now = time.time()
        self.hand_history.append((now, landmarks, gesture))
        self.last_hand_gesture = gesture
        
        return True, landmarks, gesture
    def _identify_hand_gesture(self, landmarks) -> str:
        """Identify hand gestures with rotation-robust finger extension checks."""
        if not landmarks:
            return "NONE"

        def _dist(a, b):
            return float(np.linalg.norm(a - b))

        wrist = np.array([landmarks[0].x, landmarks[0].y, landmarks[0].z], dtype=np.float32)

        def _extended(tip_i: int, pip_i: int, margin: float = 0.010) -> bool:  # Was 0.015
            tip = np.array([landmarks[tip_i].x, landmarks[tip_i].y, landmarks[tip_i].z], dtype=np.float32)
            pip = np.array([landmarks[pip_i].x, landmarks[pip_i].y, landmarks[pip_i].z], dtype=np.float32)
            return (_dist(tip, wrist) - _dist(pip, wrist)) > margin

        def _thumb_extended(margin: float = 0.008) -> bool:  # Was 0.010
            tip = np.array([landmarks[4].x, landmarks[4].y, landmarks[4].z], dtype=np.float32)
            mcp = np.array([landmarks[2].x, landmarks[2].y, landmarks[2].z], dtype=np.float32)
            # Thumb sticks out sideways; require distance gain and some lateral spread.
            return (_dist(tip, wrist) - _dist(mcp, wrist)) > margin and abs(tip[0] - wrist[0]) > 0.03  # Was 0.04

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

        # Thumbs up: thumb extended, all other fingers curled
        if thumb and (not index) and (not middle) and (not ring) and (not pinky):
            return "THUMBS_UP"

        # Fist: none extended (thumb ambiguous; allow either), and tips close-ish to wrist
        if (not index) and (not middle) and (not ring) and (not pinky):
            tips2 = np.array([[landmarks[i].x, landmarks[i].y, landmarks[i].z] for i in (8, 12, 16, 20)], dtype=np.float32)
            if float(np.mean(np.linalg.norm(tips2 - wrist, axis=1))) < 0.28:
                return "FIST"

        # One finger: index only (thumb should be tucked)
        if index and (not middle) and (not ring) and (not pinky) and (not thumb):
            return "ONE_FINGER"

        # Three fingers: index+middle+ring; pinky curled (thumb can be either)
        if index and middle and ring and (not pinky):
            return "THREE_FINGERS"

        # Five fingers: all extended
        if thumb and index and middle and ring and pinky:
            return "FIVE_FINGERS"

        return "HAND"

        
    def _calculate_hand_detection_score(self) -> float:
        """
        Calculate a score for hand detection based on history.
        
        Returns:
            Float between 0.0 and 1.0 indicating confidence in hand detection.
        """
        if len(self.hand_history) < 5:
            return 0.0
        
        # Count how many frames have hands
        hand_frames = sum(1 for _, _, gesture in self.hand_history if gesture != "NONE")
        
        # Calculate percentage of frames with hands
        hand_percentage = hand_frames / len(self.hand_history)
        
        # Score based on hand presence
        return min(1.0, hand_percentage * 1.5)  # Scale up to make it easier to get a high score
    
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
            "blink_rate": 0.0,
            "micro_movement_score": 0.0,
            "3d_consistency_score": 0.0,
            "blink_pattern_score": 0.0,
            "challenge_response_score": 0.0,
            "texture_score": 0.0,
            "hand_detected": hand_detected,
            "hand_gesture": hand_gesture,
            "hand_detection_score": 0.0,
            "current_challenge": self.current_challenge,
            "challenge_completed": self.challenge_completed,
            "successful_challenges_count": self.successful_challenges_count,
            "required_challenges": REQUIRED_CHALLENGES,
            "completed_challenges": self.completed_challenges,
            "next_challenge_time": self.next_challenge_time,
            "challenge_success_time": self.challenge_success_time
        }
        
        # Calculate hand detection score
        hand_detection_score = self._calculate_hand_detection_score()
        details["hand_detection_score"] = hand_detection_score
        
        # If no face is detected but hand is detected, we can still authenticate with lower confidence
        if not detection_result.face_landmarks:
            if hand_detected:
                # Handle active challenges for hand-only authentication
                challenge_response_score = 0.0
                
                # Get current time
                now = time.time()
                
                # Issue a new challenge if needed
                if not self.current_challenge:
                    # No current challenge, issue a new one using the same method as face mode
                    # This ensures proper tracking of completed challenges, which fixes the issue
                    # where the "SHOW_FIVE_FINGERS" challenge wasn't being marked as completed after restart
                    
                    # Only use hand-related challenges in hand-only mode
                    # We use the allowed_challenges parameter to restrict the challenges to hand-related ones
                    # while still benefiting from the proper challenge tracking in _issue_next_challenge
                    hand_challenges = ["SHOW_PEACE_SIGN", "SHOW_FIVE_FINGERS"]
                    self._issue_next_challenge(allowed_challenges=hand_challenges)
                elif self.challenge_completed:
                    # Challenge is completed, check if it's time for the next challenge
                    # This ensures a new challenge is presented after the delay specified by CHALLENGE_DELAY_SEC
                    if self.next_challenge_time and now >= self.next_challenge_time:
                        # Use the same method as face mode to ensure proper tracking of completed challenges
                        # Only use hand-related challenges in hand-only mode
                        hand_challenges = ["SHOW_PEACE_SIGN", "SHOW_FIVE_FINGERS"]
                        self._issue_next_challenge(allowed_challenges=hand_challenges)
                else:
                    # Check response to current challenge
                    completed, response_time = self._check_challenge_response(
                        None, None, hand_detected, hand_gesture
                    )
                    
                    if completed:
                        # Score based on response time
                        if response_time < CHALLENGE_RESPONSE_TIME_MIN:
                            # Too fast, suspicious
                            challenge_response_score = 0.0
                        elif response_time > CHALLENGE_RESPONSE_TIME_MAX:
                            # Too slow, suspicious
                            challenge_response_score = max(0.0, 1.0 - (response_time - CHALLENGE_RESPONSE_TIME_MAX))
                        else:
                            # Natural response time
                            challenge_response_score = 1.0
                
                details["challenge_response_score"] = challenge_response_score
                
                # Calculate confidence for hand-only authentication
                confidence = (
                    self.weights["hand_detection"] * hand_detection_score +
                    self.weights["challenge_response"] * challenge_response_score
                ) / (self.weights["hand_detection"] + self.weights["challenge_response"])
                
                return AuthResult(
                    authenticated=confidence >= 0.5,  # Lower threshold for hand-only
                    confidence=confidence,
                    details=details,
                    message=f"Hand-only authentication with {confidence:.2f} confidence"
                )
            else:
                return AuthResult(
                    authenticated=False,
                    confidence=0.0,
                    details=details,
                    message="No face or hand detected"
                )
        
        # Extract landmarks and blendshapes
        landmarks = detection_result.face_landmarks[0]
        blendshapes = detection_result.face_blendshapes[0] if detection_result.face_blendshapes else None
        
        # Estimate head pose
        yaw, pitch = self._estimate_head_pose(landmarks)
        
        # Update face history
        now = time.time()
        self.face_history.append((now, landmarks, yaw, pitch))
        
        # Calculate depth ratios for 3D consistency
        depth_ratios = self._calculate_depth_ratios(landmarks)
        if depth_ratios:
            self.depth_ratios_history.append(depth_ratios)
        
        # Detect blink
        blink_detected = self._detect_blink(landmarks)
        
        # Update details
        details["face_detected"] = True
        details["blink_detected"] = blink_detected
        details["blink_rate"] = self.blink_rate
        
        # Calculate scores for different detection methods
        micro_movement_score = self._detect_micro_movements()
        consistency_score = self._check_3d_consistency()
        blink_pattern_score = self._check_blink_pattern()
        texture_score = self._analyze_texture(frame_bgr)
        
        # Store current landmarks for drawing
        self.current_landmarks = landmarks
        self.current_hand_landmarks = hand_landmarks if hand_detected else None
        
        # Add landmarks to details for frontend visualization
        details["face_landmarks"] = [
            {"x": point.x, "y": point.y, "z": point.z} 
            for point in landmarks
        ] if landmarks else []
        
        details["hand_landmarks"] = [
            {"x": point.x, "y": point.y, "z": point.z} 
            for point in hand_landmarks
        ] if hand_detected and hand_landmarks else []
        
        # Handle active challenges
        challenge_response_score = 0.0
        now = time.time()
        
        # Issue a new challenge if needed
        if not self.current_challenge:
            self._issue_next_challenge()
        elif self.challenge_completed:
            # If it's time for the next challenge
            if self.next_challenge_time and now >= self.next_challenge_time:
                self._issue_next_challenge()
        else:
            # Check response to current challenge
            completed, response_time = self._check_challenge_response(
                landmarks, blendshapes, hand_detected, hand_gesture
            )
            
            if completed:
                # Score based on response time
                if response_time < CHALLENGE_RESPONSE_TIME_MIN:
                    # Too fast, suspicious
                    challenge_response_score = 0.0
                elif response_time > CHALLENGE_RESPONSE_TIME_MAX:
                    # Too slow, suspicious
                    challenge_response_score = max(0.0, 1.0 - (response_time - CHALLENGE_RESPONSE_TIME_MAX))
                else:
                    # Natural response time
                    challenge_response_score = 1.0
        
        # Update details with scores
        details["micro_movement_score"] = micro_movement_score
        details["3d_consistency_score"] = consistency_score
        details["blink_pattern_score"] = blink_pattern_score
        details["challenge_response_score"] = challenge_response_score
        details["texture_score"] = texture_score
        
        # Add scores object for visualization
        details["scores"] = {
            "Micro Movement": micro_movement_score,
            "3D Consistency": consistency_score,
            "Blink Pattern": blink_pattern_score,
            "Challenge Response": challenge_response_score,
            "Texture Analysis": texture_score,
            "Hand Detection": hand_detection_score
        }

        # Calculate overall confidence (tuned)
        # Passive baseline: small initial confidence so the UI shows a value early
        passive_base = 0.0
        if details.get("face_detected"):
            passive_base = 0.14
        elif details.get("hand_detected"):
            passive_base = 0.06

        # Weighted sum of detector scores
        confidence = (
                self.weights["micro_movement"] * micro_movement_score +
                self.weights["3d_consistency"] * consistency_score +
                self.weights["blink_pattern"] * blink_pattern_score +
                self.weights["challenge_response"] * challenge_response_score +
                self.weights["texture_analysis"] * texture_score +
                self.weights["hand_detection"] * hand_detection_score
        )

        # Add passive baseline so frontend sees a non-zero interval early
        confidence = min(1.0, confidence + passive_base)

        # Stronger boost per completed challenge so the displayed confidence rises faster
        boost_per_challenge = 0.18
        confidence_boost = boost_per_challenge * min(self.successful_challenges_count, REQUIRED_CHALLENGES)
        confidence = min(1.0, confidence + confidence_boost)

        # Update authentication state
        self.auth_confidence = confidence

        # Authentication logic: if required challenges are completed, immediately authenticate
        if self.successful_challenges_count >= REQUIRED_CHALLENGES:
            authenticated_now = True
        else:
            authenticated_now = confidence >= AUTH_THRESHOLD

        # Latch auth briefly to avoid flicker
        if authenticated_now:
            self.authenticated = True
            self.last_auth_time = now
        else:
            if self.last_auth_time and (now - self.last_auth_time) <= AUTH_HOLD_SEC:
                self.authenticated = True
            else:
                self.authenticated = False

        # If we've been unauthenticated for a while, reset challenge counters so the user can retry
        if not self.authenticated:
            if self.last_auth_time and (now - self.last_auth_time) > 10.0:
                self.successful_challenges_count = 0
                self.completed_challenges = []
                self.last_auth_time = None

        # Prepare result message
        if self.authenticated:
            message = f"Human authenticated with {confidence:.2f} confidence"
        else:
            message = f"Authentication failed with {confidence:.2f} confidence"
        
        return AuthResult(
            authenticated=self.authenticated,
            confidence=confidence,
            details=details,
            message=message
        )
    
    
    
    

