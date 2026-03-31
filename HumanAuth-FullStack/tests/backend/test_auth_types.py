#!/usr/bin/env python3
"""
Comprehensive test suite for auth_types.py module.
Tests the data structures and type definitions used in authentication.
"""

import unittest
import json
from dataclasses import asdict
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../HumanAuth-FullStack/backend'))

try:
    from auth_types import AuthResult, SessionSummary
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("This test requires the backend modules to be available")

class TestAuthResult(unittest.TestCase):
    """Test cases for AuthResult dataclass"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.sample_details = {
                'face_detected': True,
                'hand_detected': False,
                'confidence_score': 0.75,
                'challenge': 'BLINK_ONCE'
            }
            
            self.sample_session_summary = SessionSummary(
                final_confidence=0.85,
                auth_method='confidence_threshold',
                passive_base=0.14,
                challenge_boost=0.36,
                detector_contributions={'test': 0.5},
                final_scores={'test': 0.8},
                weights={'test': 0.2},
                session_duration=5.0,
                frames_processed=50,
                challenges_completed=2,
                challenges_required=3,
                completed_challenges=[],
                auth_threshold=0.55
            )
        except NameError:
            self.skipTest("AuthResult/SessionSummary not available")
    
    def test_auth_result_creation(self):
        """Test creating an AuthResult instance"""
        result = AuthResult(
            authenticated=True,
            confidence=0.85,
            details=self.sample_details,
            message="Authentication successful",
            session_summary=self.sample_session_summary
        )
        
        self.assertTrue(result.authenticated)
        self.assertEqual(result.confidence, 0.85)
        self.assertEqual(result.details, self.sample_details)
        self.assertEqual(result.message, "Authentication successful")
        self.assertEqual(result.session_summary, self.sample_session_summary)
    
    def test_auth_result_without_session_summary(self):
        """Test creating AuthResult without session summary"""
        result = AuthResult(
            authenticated=False,
            confidence=0.3,
            details=self.sample_details,
            message="Authentication failed",
            session_summary=None
        )
        
        self.assertFalse(result.authenticated)
        self.assertEqual(result.confidence, 0.3)
        self.assertIsNone(result.session_summary)
    
    def test_auth_result_serialization(self):
        """Test that AuthResult can be serialized to dict"""
        result = AuthResult(
            authenticated=True,
            confidence=0.85,
            details=self.sample_details,
            message="Test message",
            session_summary=self.sample_session_summary
        )
        
        # Convert to dict
        result_dict = asdict(result)
        
        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['authenticated'], True)
        self.assertEqual(result_dict['confidence'], 0.85)
        self.assertEqual(result_dict['message'], "Test message")
        self.assertIn('session_summary', result_dict)
    
    def test_auth_result_json_serialization(self):
        """Test that AuthResult can be JSON serialized"""
        result = AuthResult(
            authenticated=True,
            confidence=0.85,
            details=self.sample_details,
            message="Test message",
            session_summary=self.sample_session_summary
        )
        
        # Convert to JSON
        try:
            json_str = json.dumps(asdict(result))
            self.assertIsInstance(json_str, str)
            
            # Parse back
            parsed = json.loads(json_str)
            self.assertEqual(parsed['authenticated'], True)
            self.assertEqual(parsed['confidence'], 0.85)
        except (TypeError, ValueError) as e:
            self.fail(f"AuthResult should be JSON serializable: {e}")
    
    def test_auth_result_edge_cases(self):
        """Test AuthResult with edge case values"""
        # Test with minimum values
        result_min = AuthResult(
            authenticated=False,
            confidence=0.0,
            details={},
            message="",
            session_summary=None
        )
        
        self.assertFalse(result_min.authenticated)
        self.assertEqual(result_min.confidence, 0.0)
        self.assertEqual(result_min.details, {})
        self.assertEqual(result_min.message, "")
        
        # Test with maximum values
        result_max = AuthResult(
            authenticated=True,
            confidence=1.0,
            details={'key': 'value'},
            message="Maximum confidence achieved",
            session_summary=self.sample_session_summary
        )
        
        self.assertTrue(result_max.authenticated)
        self.assertEqual(result_max.confidence, 1.0)

class TestSessionSummary(unittest.TestCase):
    """Test cases for SessionSummary dataclass"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.sample_detector_contributions = {
                'Micro Movement': 0.05,
                '3D Consistency': 0.14,
                'Blink Pattern': 0.0,
                'Challenge Response': 0.4,
                'Texture Analysis': 0.015,
                'Hand Detection': 0.15
            }
            
            self.sample_final_scores = {
                'Micro Movement': 0.62,
                '3D Consistency': 0.93,
                'Blink Pattern': 0.0,
                'Challenge Response': 1.0,
                'Texture Analysis': 0.15,
                'Hand Detection': 1.0
            }
            
            self.sample_weights = {
                '3d_consistency': 0.15,
                'micro_movement': 0.08,
                'blink_pattern': 0.12,
                'challenge_response': 0.4,
                'texture_analysis': 0.1,
                'hand_detection': 0.15
            }
            
            self.sample_completed_challenges = [
                {
                    'challenge': 'SHOW_PEACE_SIGN',
                    'response_time': 1.42,
                    'score': 1.0,
                    'timestamp': 1771861306.029716
                },
                {
                    'challenge': 'BLINK_ONCE',
                    'response_time': 1.00,
                    'score': 1.0,
                    'timestamp': 1771861308.061176
                }
            ]
        except NameError:
            self.skipTest("SessionSummary not available")
    
    def test_session_summary_creation(self):
        """Test creating a SessionSummary instance"""
        summary = SessionSummary(
            final_confidence=0.85,
            auth_method='confidence_threshold',
            passive_base=0.14,
            challenge_boost=0.36,
            detector_contributions=self.sample_detector_contributions,
            final_scores=self.sample_final_scores,
            weights=self.sample_weights,
            session_duration=3.64,
            frames_processed=32,
            challenges_completed=2,
            challenges_required=3,
            completed_challenges=self.sample_completed_challenges,
            auth_threshold=0.55
        )
        
        self.assertEqual(summary.final_confidence, 0.85)
        self.assertEqual(summary.auth_method, 'confidence_threshold')
        self.assertEqual(summary.passive_base, 0.14)
        self.assertEqual(summary.challenge_boost, 0.36)
        self.assertEqual(summary.session_duration, 3.64)
        self.assertEqual(summary.frames_processed, 32)
        self.assertEqual(summary.challenges_completed, 2)
        self.assertEqual(summary.challenges_required, 3)
        self.assertEqual(summary.auth_threshold, 0.55)
    
    def test_session_summary_detector_data(self):
        """Test SessionSummary detector-related data"""
        summary = SessionSummary(
            final_confidence=0.85,
            auth_method='confidence_threshold',
            passive_base=0.14,
            challenge_boost=0.36,
            detector_contributions=self.sample_detector_contributions,
            final_scores=self.sample_final_scores,
            weights=self.sample_weights,
            session_duration=3.64,
            frames_processed=32,
            challenges_completed=2,
            challenges_required=3,
            completed_challenges=self.sample_completed_challenges,
            auth_threshold=0.55
        )
        
        # Test detector contributions
        self.assertIn('Micro Movement', summary.detector_contributions)
        self.assertIn('Challenge Response', summary.detector_contributions)
        self.assertEqual(summary.detector_contributions['Challenge Response'], 0.4)
        
        # Test final scores
        self.assertIn('3D Consistency', summary.final_scores)
        self.assertEqual(summary.final_scores['Challenge Response'], 1.0)
        
        # Test weights
        self.assertIn('challenge_response', summary.weights)
        self.assertEqual(summary.weights['challenge_response'], 0.4)
    
    def test_session_summary_challenge_data(self):
        """Test SessionSummary challenge-related data"""
        summary = SessionSummary(
            final_confidence=0.85,
            auth_method='confidence_threshold',
            passive_base=0.14,
            challenge_boost=0.36,
            detector_contributions=self.sample_detector_contributions,
            final_scores=self.sample_final_scores,
            weights=self.sample_weights,
            session_duration=3.64,
            frames_processed=32,
            challenges_completed=2,
            challenges_required=3,
            completed_challenges=self.sample_completed_challenges,
            auth_threshold=0.55
        )
        
        # Test completed challenges
        self.assertEqual(len(summary.completed_challenges), 2)
        self.assertEqual(summary.completed_challenges[0]['challenge'], 'SHOW_PEACE_SIGN')
        self.assertEqual(summary.completed_challenges[1]['challenge'], 'BLINK_ONCE')
        
        # Test challenge metrics
        self.assertGreater(summary.completed_challenges[0]['response_time'], 0)
        self.assertEqual(summary.completed_challenges[0]['score'], 1.0)
        self.assertIn('timestamp', summary.completed_challenges[0])
    
    def test_session_summary_serialization(self):
        """Test that SessionSummary can be serialized"""
        summary = SessionSummary(
            final_confidence=0.85,
            auth_method='confidence_threshold',
            passive_base=0.14,
            challenge_boost=0.36,
            detector_contributions=self.sample_detector_contributions,
            final_scores=self.sample_final_scores,
            weights=self.sample_weights,
            session_duration=3.64,
            frames_processed=32,
            challenges_completed=2,
            challenges_required=3,
            completed_challenges=self.sample_completed_challenges,
            auth_threshold=0.55
        )
        
        # Convert to dict
        summary_dict = asdict(summary)
        
        self.assertIsInstance(summary_dict, dict)
        self.assertEqual(summary_dict['final_confidence'], 0.85)
        self.assertEqual(summary_dict['auth_method'], 'confidence_threshold')
        self.assertIn('detector_contributions', summary_dict)
        self.assertIn('completed_challenges', summary_dict)
    
    def test_session_summary_json_serialization(self):
        """Test that SessionSummary can be JSON serialized"""
        summary = SessionSummary(
            final_confidence=0.85,
            auth_method='confidence_threshold',
            passive_base=0.14,
            challenge_boost=0.36,
            detector_contributions=self.sample_detector_contributions,
            final_scores=self.sample_final_scores,
            weights=self.sample_weights,
            session_duration=3.64,
            frames_processed=32,
            challenges_completed=2,
            challenges_required=3,
            completed_challenges=self.sample_completed_challenges,
            auth_threshold=0.55
        )
        
        # Convert to JSON
        try:
            json_str = json.dumps(asdict(summary))
            self.assertIsInstance(json_str, str)
            
            # Parse back
            parsed = json.loads(json_str)
            self.assertEqual(parsed['final_confidence'], 0.85)
            self.assertEqual(parsed['auth_method'], 'confidence_threshold')
            self.assertIn('detector_contributions', parsed)
        except (TypeError, ValueError) as e:
            self.fail(f"SessionSummary should be JSON serializable: {e}")
    
    def test_session_summary_edge_cases(self):
        """Test SessionSummary with edge case values"""
        # Test with minimal data
        summary_min = SessionSummary(
            final_confidence=0.0,
            auth_method='',
            passive_base=0.0,
            challenge_boost=0.0,
            detector_contributions={},
            final_scores={},
            weights={},
            session_duration=0.0,
            frames_processed=0,
            challenges_completed=0,
            challenges_required=1,
            completed_challenges=[],
            auth_threshold=0.5
        )
        
        self.assertEqual(summary_min.final_confidence, 0.0)
        self.assertEqual(summary_min.frames_processed, 0)
        self.assertEqual(summary_min.challenges_completed, 0)
        self.assertEqual(len(summary_min.completed_challenges), 0)
        
        # Test with maximum realistic values
        summary_max = SessionSummary(
            final_confidence=1.0,
            auth_method='confidence_threshold',
            passive_base=0.2,
            challenge_boost=0.8,
            detector_contributions=self.sample_detector_contributions,
            final_scores=self.sample_final_scores,
            weights=self.sample_weights,
            session_duration=60.0,
            frames_processed=1000,
            challenges_completed=5,
            challenges_required=5,
            completed_challenges=self.sample_completed_challenges,
            auth_threshold=0.9
        )
        
        self.assertEqual(summary_max.final_confidence, 1.0)
        self.assertEqual(summary_max.frames_processed, 1000)
        self.assertEqual(summary_max.challenges_completed, 5)

class TestDataStructureIntegration(unittest.TestCase):
    """Test cases for integration between data structures"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.sample_session_summary = SessionSummary(
                final_confidence=0.85,
                auth_method='confidence_threshold',
                passive_base=0.14,
                challenge_boost=0.36,
                detector_contributions={'test': 0.5},
                final_scores={'test': 0.8},
                weights={'test': 0.2},
                session_duration=5.0,
                frames_processed=50,
                challenges_completed=2,
                challenges_required=3,
                completed_challenges=[],
                auth_threshold=0.55
            )
        except NameError:
            self.skipTest("Data structures not available")
    
    def test_auth_result_with_session_summary(self):
        """Test AuthResult containing SessionSummary"""
        result = AuthResult(
            authenticated=True,
            confidence=0.85,
            details={'test': 'data'},
            message="Authentication successful",
            session_summary=self.sample_session_summary
        )
        
        # Verify the session summary is properly embedded
        self.assertIsNotNone(result.session_summary)
        self.assertEqual(result.session_summary.final_confidence, 0.85)
        self.assertEqual(result.session_summary.auth_method, 'confidence_threshold')
        
        # Verify serialization works with nested structure
        result_dict = asdict(result)
        self.assertIn('session_summary', result_dict)
        self.assertIsInstance(result_dict['session_summary'], dict)
        self.assertEqual(result_dict['session_summary']['final_confidence'], 0.85)
    
    def test_data_consistency(self):
        """Test consistency between AuthResult and SessionSummary data"""
        result = AuthResult(
            authenticated=True,
            confidence=0.85,
            details={'test': 'data'},
            message="Authentication successful",
            session_summary=self.sample_session_summary
        )
        
        # Confidence should match between AuthResult and SessionSummary
        self.assertEqual(result.confidence, result.session_summary.final_confidence)
        
        # Authentication status should be consistent with confidence
        if result.authenticated:
            self.assertGreaterEqual(result.confidence, result.session_summary.auth_threshold)

def run_auth_types_tests():
    """Run all auth types tests and return results"""
    print("🧪 Running Auth Types Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestAuthResult))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionSummary))
    suite.addTests(loader.loadTestsFromTestCase(TestDataStructureIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_auth_types_tests()
    sys.exit(0 if success else 1)