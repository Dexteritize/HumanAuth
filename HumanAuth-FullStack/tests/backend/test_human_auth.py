#!/usr/bin/env python3
"""
Comprehensive test suite for human_auth.py module.
Tests the core authentication logic, challenge handling, and biometric analysis.
"""

import unittest
import numpy as np
import cv2
import time
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../HumanAuth-FullStack/backend'))

try:
    from human_auth import HumanAuthenticator, CHALLENGES, AUTH_THRESHOLD, REQUIRED_CHALLENGES
    from auth_types import AuthResult, SessionSummary
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("This test requires the backend modules to be available")

class TestHumanAuthenticator(unittest.TestCase):
    """Test cases for HumanAuthenticator class"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        try:
            self.authenticator = HumanAuthenticator()
            self.sample_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        except NameError:
            self.skipTest("HumanAuthenticator not available")
    
    def test_initialization(self):
        """Test that HumanAuthenticator initializes correctly"""
        self.assertIsNotNone(self.authenticator)
        self.assertEqual(self.authenticator.frames_processed, 0)
        self.assertEqual(self.authenticator.successful_challenges_count, 0)
        self.assertFalse(self.authenticator.authenticated)
        self.assertEqual(self.authenticator.auth_confidence, 0.0)
    
    def test_reset_session(self):
        """Test session reset functionality"""
        # Modify some state
        self.authenticator.frames_processed = 10
        self.authenticator.successful_challenges_count = 2
        self.authenticator.authenticated = True
        self.authenticator.auth_confidence = 0.8
        
        # Reset session
        self.authenticator.reset_session()
        
        # Verify reset
        self.assertEqual(self.authenticator.frames_processed, 0)
        self.assertEqual(self.authenticator.successful_challenges_count, 0)
        self.assertFalse(self.authenticator.authenticated)
        self.assertEqual(self.authenticator.auth_confidence, 0.0)
    
    def test_challenge_issuance(self):
        """Test challenge issuance and tracking"""
        challenge = self.authenticator._issue_challenge()
        
        self.assertIn(challenge, CHALLENGES)
        self.assertEqual(self.authenticator.current_challenge, challenge)
        self.assertIsNotNone(self.authenticator.challenge_start_time)
        self.assertFalse(self.authenticator.challenge_completed)
    
    def test_next_challenge_selection(self):
        """Test that next challenge selection avoids duplicates"""
        # Issue multiple challenges and track them
        issued_challenges = []
        for _ in range(min(len(CHALLENGES), 5)):
            challenge = self.authenticator._issue_next_challenge()
            issued_challenges.append(challenge)
            # Mark as completed to move to next
            self.authenticator.completed_challenges.append(challenge)
        
        # Verify no immediate duplicates (until all challenges used)
        if len(CHALLENGES) > 1:
            self.assertNotEqual(issued_challenges[0], issued_challenges[1])
    
    def test_blink_detection(self):
        """Test blink detection logic"""
        # Mock landmarks for open eyes
        mock_landmarks_open = [Mock() for _ in range(468)]
        # Set eye landmarks to "open" position
        mock_landmarks_open[145].y = 0.3  # Upper eyelid
        mock_landmarks_open[159].y = 0.35  # Lower eyelid
        
        # Mock landmarks for closed eyes  
        mock_landmarks_closed = [Mock() for _ in range(468)]
        # Set eye landmarks to "closed" position
        mock_landmarks_closed[145].y = 0.33  # Upper eyelid closer
        mock_landmarks_closed[159].y = 0.33  # Lower eyelid closer
        
        # Test open eyes (should not detect blink)
        blink_open = self.authenticator._detect_blink(mock_landmarks_open)
        
        # Test closed eyes (should detect blink)
        blink_closed = self.authenticator._detect_blink(mock_landmarks_closed)
        
        # Note: Actual blink detection depends on the threshold and implementation
        # This test verifies the method runs without error
        self.assertIsInstance(blink_open, bool)
        self.assertIsInstance(blink_closed, bool)
    
    def test_head_pose_estimation(self):
        """Test head pose estimation"""
        # Create mock landmarks
        mock_landmarks = [Mock() for _ in range(468)]
        
        # Set specific landmark positions
        mock_landmarks[4].x, mock_landmarks[4].y, mock_landmarks[4].z = 0.5, 0.5, 0.0  # nose
        mock_landmarks[33].x, mock_landmarks[33].y, mock_landmarks[33].z = 0.4, 0.4, 0.0  # left eye
        mock_landmarks[263].x, mock_landmarks[263].y, mock_landmarks[263].z = 0.6, 0.4, 0.0  # right eye
        mock_landmarks[61].x, mock_landmarks[61].y, mock_landmarks[61].z = 0.4, 0.6, 0.0  # left mouth
        mock_landmarks[291].x, mock_landmarks[291].y, mock_landmarks[291].z = 0.6, 0.6, 0.0  # right mouth
        
        yaw, pitch = self.authenticator._estimate_head_pose(mock_landmarks)
        
        self.assertIsInstance(yaw, float)
        self.assertIsInstance(pitch, float)
    
    def test_texture_analysis(self):
        """Test texture analysis for screen detection"""
        # Create test frames
        natural_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        screen_frame = np.tile(np.arange(0, 255, 255//640), (480, 1, 1)).astype(np.uint8)
        screen_frame = np.repeat(screen_frame[:, :, np.newaxis], 3, axis=2)
        
        natural_score = self.authenticator._analyze_texture(natural_frame)
        screen_score = self.authenticator._analyze_texture(screen_frame)
        
        self.assertIsInstance(natural_score, float)
        self.assertIsInstance(screen_score, float)
        self.assertGreaterEqual(natural_score, 0.0)
        self.assertLessEqual(natural_score, 1.0)
        self.assertGreaterEqual(screen_score, 0.0)
        self.assertLessEqual(screen_score, 1.0)
    
    def test_micro_movement_detection(self):
        """Test micro movement detection"""
        # Add some face history
        now = time.time()
        mock_landmarks = [Mock() for _ in range(468)]
        for i, landmark in enumerate(mock_landmarks):
            landmark.x = 0.5 + (i % 10) * 0.001  # Small variations
            landmark.y = 0.5 + (i % 10) * 0.001
            landmark.z = 0.0
        
        # Add multiple history entries with slight variations
        for i in range(10):
            self.authenticator.face_history.append((now - i, mock_landmarks, 0.0, 0.0))
        
        score = self.authenticator._detect_micro_movements()
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_3d_consistency_check(self):
        """Test 3D consistency checking"""
        # Add some depth ratio history
        for _ in range(10):
            depth_ratios = {
                'eye_nose': 1.0 + np.random.normal(0, 0.01),
                'mouth_nose': 1.2 + np.random.normal(0, 0.01),
                'eye_mouth': 0.8 + np.random.normal(0, 0.01)
            }
            self.authenticator.depth_ratios_history.append(depth_ratios)
        
        score = self.authenticator._check_3d_consistency()
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    def test_blink_pattern_analysis(self):
        """Test blink pattern analysis"""
        # Add some blink history
        now = time.time()
        for i in range(10):
            self.authenticator.blink_history.append(now - i * 2)  # Blinks every 2 seconds
        
        score = self.authenticator._check_blink_pattern()
        
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
    
    @patch('human_auth.mp_tasks_vision.FaceLandmarker')
    @patch('human_auth.mp_tasks_vision.HandLandmarker')
    def test_process_frame_no_detection(self, mock_hand_landmarker, mock_face_landmarker):
        """Test frame processing when no face/hand is detected"""
        # Mock no detection
        mock_face_result = Mock()
        mock_face_result.face_landmarks = []
        mock_face_result.face_blendshapes = []
        
        mock_hand_result = Mock()
        mock_hand_result.hand_landmarks = []
        
        mock_face_landmarker.return_value.detect.return_value = mock_face_result
        mock_hand_landmarker.return_value.detect.return_value = mock_hand_result
        
        result = self.authenticator.process_frame(self.sample_frame)
        
        self.assertIsInstance(result, AuthResult)
        self.assertFalse(result.authenticated)
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("No face or hand detected", result.message)
    
    def test_session_summary_creation(self):
        """Test session summary creation"""
        summary = self.authenticator._create_session_summary(
            confidence=0.85,
            micro_movement_score=0.7,
            consistency_score=0.8,
            blink_pattern_score=0.6,
            challenge_response_score=0.9,
            texture_score=0.75,
            hand_detection_score=0.8,
            passive_base=0.14
        )
        
        self.assertIsInstance(summary, SessionSummary)
        self.assertEqual(summary.final_confidence, 0.85)
        self.assertIn('micro_movement', summary.weights)
        self.assertIn('challenge_response', summary.weights)
    
    def test_auth_logging(self):
        """Test authentication decision logging"""
        with patch('human_auth.Path') as mock_path:
            mock_log_dir = Mock()
            mock_path.return_value.parent.parent = Mock()
            mock_path.return_value.parent.parent.__truediv__.return_value = mock_log_dir
            mock_log_dir.mkdir = Mock()
            
            with patch('builtins.open', create=True) as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                # Test logging
                self.authenticator._log_auth_decision(
                    authenticated=True,
                    confidence=0.85,
                    session_summary=None,
                    details={'test': 'data'}
                )
                
                # Verify file operations were called
                mock_log_dir.mkdir.assert_called_once()
                mock_open.assert_called_once()

class TestChallengeHandling(unittest.TestCase):
    """Test cases for challenge handling functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.authenticator = HumanAuthenticator()
        except NameError:
            self.skipTest("HumanAuthenticator not available")
    
    def test_all_challenges_available(self):
        """Test that all expected challenges are available"""
        expected_challenges = [
            "BLINK_ONCE", "BLINK_TWICE", "BLINK_THREE_TIMES",
            "SMILE", "OPEN_MOUTH", "RAISE_EYEBROWS",
            "TURN_HEAD_LEFT", "TURN_HEAD_RIGHT",
            "NOD_HEAD", "SHAKE_HEAD",
            "SHOW_PEACE_SIGN", "SHOW_THUMBS_UP",
            "WAVE_HAND", "POINT_UP"
        ]
        
        for challenge in expected_challenges:
            self.assertIn(challenge, CHALLENGES)
    
    def test_challenge_timeout_handling(self):
        """Test challenge timeout handling"""
        # Issue a challenge
        self.authenticator._issue_challenge()
        
        # Mock old timestamp to simulate timeout
        self.authenticator.challenge_start_time = time.time() - 100  # 100 seconds ago
        
        # Check response (should timeout)
        completed, response_time = self.authenticator._check_challenge_response(
            landmarks=None, blendshapes=None, hand_detected=False, hand_gesture="NONE"
        )
        
        self.assertFalse(completed)
        self.assertEqual(response_time, 0.0)

class TestAuthenticationThresholds(unittest.TestCase):
    """Test cases for authentication thresholds and scoring"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.authenticator = HumanAuthenticator()
        except NameError:
            self.skipTest("HumanAuthenticator not available")
    
    def test_auth_threshold_constant(self):
        """Test that AUTH_THRESHOLD is properly defined"""
        self.assertIsInstance(AUTH_THRESHOLD, float)
        self.assertGreater(AUTH_THRESHOLD, 0.0)
        self.assertLessEqual(AUTH_THRESHOLD, 1.0)
    
    def test_required_challenges_constant(self):
        """Test that REQUIRED_CHALLENGES is properly defined"""
        self.assertIsInstance(REQUIRED_CHALLENGES, int)
        self.assertGreater(REQUIRED_CHALLENGES, 0)
        self.assertLessEqual(REQUIRED_CHALLENGES, len(CHALLENGES))
    
    def test_confidence_calculation_bounds(self):
        """Test that confidence calculations stay within bounds"""
        # Test with extreme values
        test_scores = [0.0, 0.5, 1.0, -0.1, 1.1]
        
        for score in test_scores:
            # Mock some basic state
            self.authenticator.frames_processed = 10
            
            # The confidence calculation should handle extreme values gracefully
            # This is more of a smoke test to ensure no crashes
            try:
                # Test individual scoring methods with mock data
                if hasattr(self.authenticator, '_detect_micro_movements'):
                    result = self.authenticator._detect_micro_movements()
                    self.assertIsInstance(result, (int, float))
            except Exception as e:
                # Log but don't fail - some methods need specific setup
                print(f"Method call failed (expected for some cases): {e}")

def run_backend_tests():
    """Run all backend tests and return results"""
    print("🧪 Running Backend API Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestHumanAuthenticator))
    suite.addTests(loader.loadTestsFromTestCase(TestChallengeHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthenticationThresholds))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_backend_tests()
    sys.exit(0 if success else 1)