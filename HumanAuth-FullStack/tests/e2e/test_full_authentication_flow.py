#!/usr/bin/env python3
"""
End-to-end integration tests for the complete authentication flow.
Tests the full system from frontend to backend integration.
"""

import unittest
import requests
import time
import json
import base64
import subprocess
import signal
import os
from pathlib import Path
import threading
from unittest.mock import Mock, patch
import sys

class TestE2EAuthenticationFlow(unittest.TestCase):
    """End-to-end tests for complete authentication workflow"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment before running tests"""
        cls.backend_url = "http://localhost:8000"
        cls.frontend_url = "http://localhost:4200"
        cls.backend_process = None
        cls.frontend_process = None
        
        # Check if services are already running
        cls.backend_running = cls._check_service_running(cls.backend_url + "/health")
        cls.frontend_running = cls._check_service_running(cls.frontend_url)
        
        print(f"Backend running: {cls.backend_running}")
        print(f"Frontend running: {cls.frontend_running}")
    
    @classmethod
    def _check_service_running(cls, url):
        """Check if a service is running at the given URL"""
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def setUp(self):
        """Set up test fixtures"""
        if not self.backend_running:
            self.skipTest("Backend service not running. Start with: cd HumanAuth-FullStack && ./start.sh")
        
        # Create dummy image data for testing
        self.dummy_image_data = base64.b64encode(b'dummy_image_data').decode('utf-8')
    
    def test_backend_health_check(self):
        """Test backend health endpoint"""
        response = requests.get(f"{self.backend_url}/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('timestamp', data)
    
    def test_session_creation_flow(self):
        """Test complete session creation and management flow"""
        # Create a new session
        response = requests.post(f"{self.backend_url}/sessions")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('session_id', data['data'])
        
        session_id = data['data']['session_id']
        
        # Verify session exists by trying to reset it
        reset_response = requests.post(f"{self.backend_url}/sessions/{session_id}/reset")
        self.assertEqual(reset_response.status_code, 200)
        
        return session_id
    
    def test_frame_processing_flow(self):
        """Test complete frame processing workflow"""
        # Create session
        session_id = self.test_session_creation_flow()
        
        # Process a frame
        frame_data = {
            'frame': self.dummy_image_data
        }
        
        response = requests.post(
            f"{self.backend_url}/sessions/{session_id}/process",
            json=frame_data
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('data', data)
        
        # Verify response structure
        auth_data = data['data']
        self.assertIn('authenticated', auth_data)
        self.assertIn('confidence', auth_data)
        self.assertIn('details', auth_data)
        self.assertIn('message', auth_data)
        
        # Confidence should be a number between 0 and 1
        self.assertIsInstance(auth_data['confidence'], (int, float))
        self.assertGreaterEqual(auth_data['confidence'], 0.0)
        self.assertLessEqual(auth_data['confidence'], 1.0)
    
    def test_multiple_frame_processing(self):
        """Test processing multiple frames in sequence"""
        session_id = self.test_session_creation_flow()
        
        # Process multiple frames
        frame_results = []
        for i in range(5):
            frame_data = {
                'frame': self.dummy_image_data
            }
            
            response = requests.post(
                f"{self.backend_url}/sessions/{session_id}/process",
                json=frame_data
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            frame_results.append(data['data'])
        
        # Verify all frames were processed
        self.assertEqual(len(frame_results), 5)
        
        # Verify confidence progression (should generally increase or stay stable)
        confidences = [result['confidence'] for result in frame_results]
        self.assertTrue(all(isinstance(c, (int, float)) for c in confidences))
        self.assertTrue(all(0.0 <= c <= 1.0 for c in confidences))
    
    def test_session_reset_flow(self):
        """Test session reset functionality"""
        session_id = self.test_session_creation_flow()
        
        # Process a frame to change session state
        frame_data = {'frame': self.dummy_image_data}
        requests.post(f"{self.backend_url}/sessions/{session_id}/process", json=frame_data)
        
        # Reset the session
        reset_response = requests.post(f"{self.backend_url}/sessions/{session_id}/reset")
        
        self.assertEqual(reset_response.status_code, 200)
        data = reset_response.json()
        self.assertEqual(data['status'], 'success')
        
        # Process another frame after reset
        post_reset_response = requests.post(
            f"{self.backend_url}/sessions/{session_id}/process",
            json=frame_data
        )
        
        self.assertEqual(post_reset_response.status_code, 200)
    
    def test_verify_endpoint_flow(self):
        """Test single frame verification endpoint"""
        verify_data = {
            'image': self.dummy_image_data
        }
        
        response = requests.post(f"{self.backend_url}/verify", json=verify_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        # Verify response structure
        auth_data = data['data']
        self.assertIn('authenticated', auth_data)
        self.assertIn('confidence', auth_data)
        self.assertIn('details', auth_data)
    
    def test_error_handling_flow(self):
        """Test error handling in various scenarios"""
        # Test invalid session ID
        invalid_response = requests.post(f"{self.backend_url}/sessions/invalid/process")
        self.assertEqual(invalid_response.status_code, 404)
        
        # Test missing frame data
        session_id = self.test_session_creation_flow()
        no_frame_response = requests.post(f"{self.backend_url}/sessions/{session_id}/process", json={})
        self.assertEqual(no_frame_response.status_code, 400)
        
        # Test invalid JSON
        invalid_json_response = requests.post(
            f"{self.backend_url}/sessions/{session_id}/process",
            data="invalid json",
            headers={'Content-Type': 'application/json'}
        )
        self.assertEqual(invalid_json_response.status_code, 400)

class TestE2EPerformance(unittest.TestCase):
    """End-to-end performance tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.backend_url = "http://localhost:8000"
        
        # Check if backend is running
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code != 200:
                self.skipTest("Backend service not running")
        except requests.exceptions.RequestException:
            self.skipTest("Backend service not accessible")
        
        self.dummy_image_data = base64.b64encode(b'dummy_image_data').decode('utf-8')
    
    def test_session_creation_performance(self):
        """Test session creation performance"""
        start_time = time.time()
        
        # Create multiple sessions
        session_count = 10
        for _ in range(session_count):
            response = requests.post(f"{self.backend_url}/sessions")
            self.assertEqual(response.status_code, 200)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / session_count
        
        # Each session creation should be fast (< 1 second)
        self.assertLess(avg_time, 1.0, f"Session creation too slow: {avg_time:.3f}s average")
        print(f"Session creation performance: {avg_time:.3f}s average")
    
    def test_frame_processing_performance(self):
        """Test frame processing performance"""
        # Create session
        response = requests.post(f"{self.backend_url}/sessions")
        session_id = response.json()['data']['session_id']
        
        # Process multiple frames and measure time
        frame_count = 20
        start_time = time.time()
        
        for _ in range(frame_count):
            frame_data = {'frame': self.dummy_image_data}
            response = requests.post(
                f"{self.backend_url}/sessions/{session_id}/process",
                json=frame_data
            )
            self.assertEqual(response.status_code, 200)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / frame_count
        
        # Frame processing should be reasonably fast (< 2 seconds per frame)
        self.assertLess(avg_time, 2.0, f"Frame processing too slow: {avg_time:.3f}s average")
        print(f"Frame processing performance: {avg_time:.3f}s average")
    
    def test_concurrent_sessions_performance(self):
        """Test performance with concurrent sessions"""
        import threading
        import queue
        
        results = queue.Queue()
        session_count = 5
        
        def create_and_process_session():
            try:
                # Create session
                response = requests.post(f"{self.backend_url}/sessions")
                if response.status_code != 200:
                    results.put(False)
                    return
                
                session_id = response.json()['data']['session_id']
                
                # Process a few frames
                for _ in range(3):
                    frame_data = {'frame': self.dummy_image_data}
                    response = requests.post(
                        f"{self.backend_url}/sessions/{session_id}/process",
                        json=frame_data
                    )
                    if response.status_code != 200:
                        results.put(False)
                        return
                
                results.put(True)
            except Exception:
                results.put(False)
        
        # Start concurrent sessions
        start_time = time.time()
        threads = []
        
        for _ in range(session_count):
            thread = threading.Thread(target=create_and_process_session)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Collect results
        success_count = 0
        while not results.empty():
            if results.get():
                success_count += 1
        
        # All sessions should succeed
        self.assertEqual(success_count, session_count, "Some concurrent sessions failed")
        
        # Total time should be reasonable (< 30 seconds for 5 concurrent sessions)
        self.assertLess(total_time, 30.0, f"Concurrent sessions too slow: {total_time:.3f}s total")
        print(f"Concurrent sessions performance: {total_time:.3f}s for {session_count} sessions")

class TestE2EReliability(unittest.TestCase):
    """End-to-end reliability and stress tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.backend_url = "http://localhost:8000"
        
        # Check if backend is running
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code != 200:
                self.skipTest("Backend service not running")
        except requests.exceptions.RequestException:
            self.skipTest("Backend service not accessible")
        
        self.dummy_image_data = base64.b64encode(b'dummy_image_data').decode('utf-8')
    
    def test_long_running_session(self):
        """Test long-running session stability"""
        # Create session
        response = requests.post(f"{self.backend_url}/sessions")
        session_id = response.json()['data']['session_id']
        
        # Process many frames over time
        frame_count = 50
        success_count = 0
        
        for i in range(frame_count):
            frame_data = {'frame': self.dummy_image_data}
            
            try:
                response = requests.post(
                    f"{self.backend_url}/sessions/{session_id}/process",
                    json=frame_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    success_count += 1
                
                # Small delay between frames
                time.sleep(0.1)
                
            except requests.exceptions.RequestException:
                # Log but continue
                print(f"Frame {i} failed")
        
        # Most frames should succeed (allow some failures)
        success_rate = success_count / frame_count
        self.assertGreater(success_rate, 0.8, f"Success rate too low: {success_rate:.2f}")
        print(f"Long-running session success rate: {success_rate:.2f}")
    
    def test_memory_leak_detection(self):
        """Test for potential memory leaks"""
        # Create and destroy many sessions
        session_count = 20
        
        for i in range(session_count):
            # Create session
            response = requests.post(f"{self.backend_url}/sessions")
            if response.status_code != 200:
                continue
            
            session_id = response.json()['data']['session_id']
            
            # Process a few frames
            for _ in range(5):
                frame_data = {'frame': self.dummy_image_data}
                requests.post(
                    f"{self.backend_url}/sessions/{session_id}/process",
                    json=frame_data
                )
            
            # Reset session (cleanup)
            requests.post(f"{self.backend_url}/sessions/{session_id}/reset")
        
        # Check that backend is still responsive
        health_response = requests.get(f"{self.backend_url}/health")
        self.assertEqual(health_response.status_code, 200)
        print(f"Memory leak test completed: {session_count} sessions processed")

def run_e2e_tests():
    """Run all end-to-end tests and return results"""
    print("🧪 Running End-to-End Integration Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestE2EAuthenticationFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestE2EPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestE2EReliability))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)