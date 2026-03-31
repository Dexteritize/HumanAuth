#!/usr/bin/env python3
"""
Comprehensive test suite for app.py module.
Tests the Flask API endpoints, session management, and request handling.
"""

import unittest
import json
import base64
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../HumanAuth-FullStack/backend'))

try:
    from app import app, sessions, cleanup_old_sessions
    from auth_types import AuthResult, SessionSummary
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    print("This test requires the backend modules to be available")

class TestFlaskAPI(unittest.TestCase):
    """Test cases for Flask API endpoints"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        try:
            self.app = app
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
            
            # Clear sessions before each test
            sessions.clear()
        except NameError:
            self.skipTest("Flask app not available")
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
    
    def test_cors_headers(self):
        """Test that CORS headers are properly set"""
        response = self.client.get('/health')
        
        self.assertIn('Access-Control-Allow-Origin', response.headers)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
    
    def test_options_request(self):
        """Test OPTIONS request handling for CORS preflight"""
        response = self.client.options('/sessions')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('Access-Control-Allow-Methods', response.headers)
        self.assertIn('Access-Control-Allow-Headers', response.headers)

class TestSessionManagement(unittest.TestCase):
    """Test cases for session management"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.app = app
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
            sessions.clear()
        except NameError:
            self.skipTest("Flask app not available")
    
    def test_create_session(self):
        """Test session creation endpoint"""
        response = self.client.post('/sessions')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('session_id', data['data'])
        
        # Verify session was created
        session_id = data['data']['session_id']
        self.assertIn(session_id, sessions)
    
    def test_session_id_format(self):
        """Test that session IDs are properly formatted"""
        response = self.client.post('/sessions')
        data = json.loads(response.data)
        session_id = data['data']['session_id']
        
        # Session ID should be a string of reasonable length
        self.assertIsInstance(session_id, str)
        self.assertGreater(len(session_id), 10)  # Should be reasonably long
        self.assertLess(len(session_id), 100)    # But not too long
    
    def test_multiple_sessions(self):
        """Test creating multiple sessions"""
        session_ids = []
        
        for _ in range(3):
            response = self.client.post('/sessions')
            data = json.loads(response.data)
            session_ids.append(data['data']['session_id'])
        
        # All session IDs should be unique
        self.assertEqual(len(session_ids), len(set(session_ids)))
        
        # All sessions should exist
        for session_id in session_ids:
            self.assertIn(session_id, sessions)
    
    def test_session_reset(self):
        """Test session reset functionality"""
        # Create a session
        response = self.client.post('/sessions')
        data = json.loads(response.data)
        session_id = data['data']['session_id']
        
        # Reset the session
        response = self.client.post(f'/sessions/{session_id}/reset')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
    
    def test_reset_nonexistent_session(self):
        """Test resetting a session that doesn't exist"""
        response = self.client.post('/sessions/nonexistent/reset')
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('not found', data['message'].lower())

class TestFrameProcessing(unittest.TestCase):
    """Test cases for frame processing endpoints"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.app = app
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
            sessions.clear()
            
            # Create a test session
            response = self.client.post('/sessions')
            data = json.loads(response.data)
            self.session_id = data['data']['session_id']
            
            # Create a dummy base64 image
            self.dummy_frame = base64.b64encode(b'dummy_image_data').decode('utf-8')
        except NameError:
            self.skipTest("Flask app not available")
    
    @patch('app.sessions')
    def test_process_frame_success(self, mock_sessions):
        """Test successful frame processing"""
        # Mock authenticator and result
        mock_authenticator = Mock()
        mock_result = AuthResult(
            authenticated=False,
            confidence=0.5,
            details={'test': 'data'},
            message='Processing frame',
            session_summary=None
        )
        mock_authenticator.process_frame.return_value = mock_result
        
        mock_sessions.__getitem__.return_value = mock_authenticator
        mock_sessions.__contains__.return_value = True
        
        # Send frame processing request
        response = self.client.post(
            f'/sessions/{self.session_id}/process',
            json={'frame': self.dummy_frame}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
    
    def test_process_frame_no_session(self):
        """Test frame processing with invalid session"""
        response = self.client.post(
            '/sessions/invalid/process',
            json={'frame': self.dummy_frame}
        )
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
    
    def test_process_frame_no_frame_data(self):
        """Test frame processing without frame data"""
        response = self.client.post(
            f'/sessions/{self.session_id}/process',
            json={}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('frame', data['message'].lower())
    
    def test_process_frame_invalid_json(self):
        """Test frame processing with invalid JSON"""
        response = self.client.post(
            f'/sessions/{self.session_id}/process',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    @patch('app.sessions')
    def test_process_frame_with_session_summary(self, mock_sessions):
        """Test frame processing that returns session summary"""
        # Mock authenticator and result with session summary
        mock_authenticator = Mock()
        mock_summary = SessionSummary(
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
        mock_result = AuthResult(
            authenticated=True,
            confidence=0.85,
            details={'test': 'data'},
            message='Authentication successful',
            session_summary=mock_summary
        )
        mock_authenticator.process_frame.return_value = mock_result
        
        mock_sessions.__getitem__.return_value = mock_authenticator
        mock_sessions.__contains__.return_value = True
        
        # Send frame processing request
        response = self.client.post(
            f'/sessions/{self.session_id}/process',
            json={'frame': self.dummy_frame}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(data['data']['authenticated'])
        self.assertIn('session_summary', data['data'])

class TestVerifyEndpoint(unittest.TestCase):
    """Test cases for the verify endpoint (single frame verification)"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.app = app
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
            
            # Create a dummy base64 image
            self.dummy_frame = base64.b64encode(b'dummy_image_data').decode('utf-8')
        except NameError:
            self.skipTest("Flask app not available")
    
    @patch('app.HumanAuthenticator')
    def test_verify_frame_success(self, mock_authenticator_class):
        """Test successful single frame verification"""
        # Mock authenticator and result
        mock_authenticator = Mock()
        mock_result = AuthResult(
            authenticated=False,
            confidence=0.3,
            details={'test': 'data'},
            message='Single frame processed',
            session_summary=None
        )
        mock_authenticator.process_frame.return_value = mock_result
        mock_authenticator_class.return_value = mock_authenticator
        
        # Send verification request
        response = self.client.post(
            '/verify',
            json={'image': self.dummy_frame}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
    
    def test_verify_frame_no_image(self):
        """Test verification without image data"""
        response = self.client.post('/verify', json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')
        self.assertIn('image', data['message'].lower())

class TestSessionCleanup(unittest.TestCase):
    """Test cases for session cleanup functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            sessions.clear()
        except NameError:
            self.skipTest("Sessions not available")
    
    def test_cleanup_old_sessions(self):
        """Test cleanup of old sessions"""
        # Add some mock sessions with different timestamps
        current_time = time.time()
        
        # Recent session (should not be cleaned up)
        sessions['recent'] = Mock()
        sessions['recent'].session_start_time = current_time - 300  # 5 minutes ago
        
        # Old session (should be cleaned up)
        sessions['old'] = Mock()
        sessions['old'].session_start_time = current_time - 7200  # 2 hours ago
        
        # Run cleanup
        cleanup_old_sessions()
        
        # Recent session should remain
        self.assertIn('recent', sessions)
        
        # Old session should be removed
        self.assertNotIn('old', sessions)
    
    def test_cleanup_with_no_sessions(self):
        """Test cleanup when no sessions exist"""
        sessions.clear()
        
        # Should not raise any errors
        try:
            cleanup_old_sessions()
        except Exception as e:
            self.fail(f"cleanup_old_sessions raised an exception: {e}")
    
    def test_cleanup_with_invalid_session_data(self):
        """Test cleanup with sessions that have invalid data"""
        # Add session without session_start_time
        sessions['invalid'] = Mock()
        del sessions['invalid'].session_start_time
        
        # Should handle gracefully
        try:
            cleanup_old_sessions()
        except Exception as e:
            self.fail(f"cleanup_old_sessions should handle invalid data gracefully: {e}")

class TestErrorHandling(unittest.TestCase):
    """Test cases for error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        try:
            self.app = app
            self.app.config['TESTING'] = True
            self.client = self.app.test_client()
        except NameError:
            self.skipTest("Flask app not available")
    
    def test_404_handling(self):
        """Test 404 error handling"""
        response = self.client.get('/nonexistent-endpoint')
        
        self.assertEqual(response.status_code, 404)
    
    def test_method_not_allowed(self):
        """Test method not allowed handling"""
        # Try GET on POST-only endpoint
        response = self.client.get('/sessions')
        
        self.assertEqual(response.status_code, 405)
    
    @patch('app.sessions')
    def test_internal_server_error_handling(self, mock_sessions):
        """Test internal server error handling"""
        # Mock an exception during frame processing
        mock_sessions.__contains__.return_value = True
        mock_authenticator = Mock()
        mock_authenticator.process_frame.side_effect = Exception("Test error")
        mock_sessions.__getitem__.return_value = mock_authenticator
        
        # Create session first
        response = self.client.post('/sessions')
        data = json.loads(response.data)
        session_id = data['data']['session_id']
        
        # Try to process frame (should handle error gracefully)
        response = self.client.post(
            f'/sessions/{session_id}/process',
            json={'frame': base64.b64encode(b'dummy').decode('utf-8')}
        )
        
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'error')

def run_app_tests():
    """Run all Flask app tests and return results"""
    print("🧪 Running Flask API Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskAPI))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestFrameProcessing))
    suite.addTests(loader.loadTestsFromTestCase(TestVerifyEndpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestSessionCleanup))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_app_tests()
    sys.exit(0 if success else 1)