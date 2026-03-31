#!/usr/bin/env python3
"""
Test configuration and utilities for HumanAuth test suite.
Provides common configuration, test data, and utility functions.
"""

import os
import json
import base64
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from unittest.mock import Mock

# Test configuration constants
TEST_CONFIG = {
    'backend_url': 'http://localhost:8000',
    'frontend_url': 'http://localhost:4200',
    'timeout': 30,
    'retry_attempts': 3,
    'retry_delay': 1.0,
    'test_data_dir': Path(__file__).parent / 'test_data',
    'reports_dir': Path(__file__).parent.parent / 'reports',
    'logs_dir': Path(__file__).parent.parent / 'logs'
}

# Test data samples
TEST_DATA = {
    'dummy_image_small': base64.b64encode(b'dummy_image_data').decode('utf-8'),
    'dummy_image_medium': base64.b64encode(b'dummy_image_data' * 100).decode('utf-8'),
    'dummy_image_large': base64.b64encode(b'dummy_image_data' * 1000).decode('utf-8'),
    'invalid_base64': 'not_base64_at_all',
    'empty_string': '',
    'null_value': None,
    'malformed_json': '{"frame": "test"',  # Missing closing brace
    'valid_session_data': {
        'frame': base64.b64encode(b'test_frame_data').decode('utf-8')
    }
}

# Security test payloads
SECURITY_PAYLOADS = {
    'sql_injection': [
        "'; DROP TABLE sessions; --",
        "' OR '1'='1",
        "'; SELECT * FROM users; --",
        "' UNION SELECT * FROM sessions --",
        "admin'--",
        "' OR 1=1 --"
    ],
    'xss': [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "';alert('XSS');//",
        "<svg onload=alert('XSS')>",
        "<%2Fscript%3E%3Cscript%3Ealert('XSS')%3C%2Fscript%3E"
    ],
    'command_injection': [
        "; ls -la",
        "| cat /etc/passwd",
        "&& whoami",
        "; rm -rf /",
        "$(cat /etc/passwd)",
        "`whoami`"
    ],
    'path_traversal': [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "....//....//....//etc/passwd",
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
    ]
}

@dataclass
class TestResult:
    """Test result data structure"""
    name: str
    success: bool
    duration: float
    message: str = ""
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class TestUtilities:
    """Utility functions for testing"""
    
    @staticmethod
    def create_mock_landmarks(count: int = 468) -> List[Mock]:
        """Create mock face landmarks for testing"""
        landmarks = []
        for i in range(count):
            mock_landmark = Mock()
            mock_landmark.x = 0.5 + (i % 10) * 0.01
            mock_landmark.y = 0.5 + (i % 10) * 0.01
            mock_landmark.z = 0.0
            landmarks.append(mock_landmark)
        return landmarks
    
    @staticmethod
    def create_mock_hand_landmarks(count: int = 21) -> List[Mock]:
        """Create mock hand landmarks for testing"""
        landmarks = []
        for i in range(count):
            mock_landmark = Mock()
            mock_landmark.x = 0.3 + (i % 5) * 0.02
            mock_landmark.y = 0.3 + (i % 5) * 0.02
            mock_landmark.z = 0.0
            landmarks.append(mock_landmark)
        return landmarks
    
    @staticmethod
    def create_mock_auth_result(authenticated: bool = True, confidence: float = 0.85) -> Dict[str, Any]:
        """Create mock authentication result for testing"""
        return {
            'authenticated': authenticated,
            'confidence': confidence,
            'details': {
                'face_detected': True,
                'hand_detected': False,
                'current_challenge': 'BLINK_ONCE',
                'challenge_completed': True,
                'successful_challenges_count': 2,
                'required_challenges': 3,
                'scores': {
                    'Micro Movement': 0.62,
                    '3D Consistency': 0.93,
                    'Blink Pattern': 0.0,
                    'Challenge Response': 1.0,
                    'Texture Analysis': 0.15,
                    'Hand Detection': 1.0
                }
            },
            'message': 'Authentication successful' if authenticated else 'Authentication failed',
            'session_summary': {
                'final_confidence': confidence,
                'auth_method': 'confidence_threshold',
                'passive_base': 0.14,
                'challenge_boost': 0.36,
                'detector_contributions': {
                    'Micro Movement': 0.05,
                    '3D Consistency': 0.14,
                    'Challenge Response': 0.4
                },
                'final_scores': {
                    'Micro Movement': 0.62,
                    '3D Consistency': 0.93,
                    'Challenge Response': 1.0
                },
                'session_duration': 3.64,
                'frames_processed': 32,
                'challenges_completed': 2,
                'challenges_required': 3
            } if authenticated else None
        }
    
    @staticmethod
    def wait_for_condition(condition_func, timeout: float = 10.0, interval: float = 0.1) -> bool:
        """Wait for a condition to become true with timeout"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False
    
    @staticmethod
    def retry_operation(operation_func, max_attempts: int = 3, delay: float = 1.0):
        """Retry an operation with exponential backoff"""
        for attempt in range(max_attempts):
            try:
                return operation_func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(delay * (2 ** attempt))
    
    @staticmethod
    def create_test_session(backend_url: str) -> Optional[str]:
        """Create a test session and return session ID"""
        try:
            import requests
            response = requests.post(f"{backend_url}/sessions", timeout=10)
            if response.status_code == 200:
                return response.json()['data']['session_id']
        except Exception:
            pass
        return None
    
    @staticmethod
    def cleanup_test_session(backend_url: str, session_id: str) -> bool:
        """Clean up a test session"""
        try:
            import requests
            response = requests.post(f"{backend_url}/sessions/{session_id}/reset", timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    @staticmethod
    def measure_performance(operation_func, iterations: int = 10) -> Dict[str, float]:
        """Measure performance of an operation"""
        times = []
        
        for _ in range(iterations):
            start_time = time.time()
            try:
                operation_func()
                end_time = time.time()
                times.append(end_time - start_time)
            except Exception:
                # Skip failed operations in performance measurement
                continue
        
        if not times:
            return {'avg': 0.0, 'min': 0.0, 'max': 0.0, 'count': 0}
        
        return {
            'avg': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
            'count': len(times)
        }
    
    @staticmethod
    def validate_response_structure(response_data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate that response has required structure"""
        for field in required_fields:
            if '.' in field:
                # Handle nested fields like 'data.session_id'
                parts = field.split('.')
                current = response_data
                for part in parts:
                    if not isinstance(current, dict) or part not in current:
                        return False
                    current = current[part]
            else:
                if field not in response_data:
                    return False
        return True
    
    @staticmethod
    def generate_test_report(results: List[TestResult], output_file: Optional[Path] = None) -> Dict[str, Any]:
        """Generate a comprehensive test report"""
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests
        
        total_duration = sum(r.duration for r in results)
        avg_duration = total_duration / total_tests if total_tests > 0 else 0
        
        report = {
            'timestamp': time.time(),
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': failed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                'total_duration': total_duration,
                'average_duration': avg_duration
            },
            'results': [
                {
                    'name': r.name,
                    'success': r.success,
                    'duration': r.duration,
                    'message': r.message,
                    'details': r.details
                }
                for r in results
            ]
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report

class MockServices:
    """Mock services for testing"""
    
    @staticmethod
    def create_mock_camera_service():
        """Create mock camera service"""
        mock_camera = Mock()
        mock_camera.start.return_value = True
        mock_camera.stop.return_value = True
        mock_camera.capture.return_value = TEST_DATA['dummy_image_medium']
        return mock_camera
    
    @staticmethod
    def create_mock_auth_service():
        """Create mock authentication service"""
        mock_auth = Mock()
        mock_auth.initialize.return_value = True
        mock_auth.startAuth.return_value = True
        mock_auth.processFrame.return_value = TestUtilities.create_mock_auth_result()
        mock_auth.resetAuth.return_value = True
        mock_auth.disconnect.return_value = True
        return mock_auth
    
    @staticmethod
    def create_mock_http_response(status_code: int = 200, data: Dict[str, Any] = None):
        """Create mock HTTP response"""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = data or {'status': 'success', 'data': {}}
        mock_response.text = json.dumps(data or {})
        mock_response.headers = {'Content-Type': 'application/json'}
        return mock_response

class TestEnvironment:
    """Test environment management"""
    
    def __init__(self):
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary test directories"""
        for dir_key in ['test_data_dir', 'reports_dir', 'logs_dir']:
            directory = TEST_CONFIG[dir_key]
            directory.mkdir(parents=True, exist_ok=True)
    
    def cleanup_test_files(self, pattern: str = "test_*"):
        """Clean up test files matching pattern"""
        for directory in [TEST_CONFIG['test_data_dir'], TEST_CONFIG['reports_dir'], TEST_CONFIG['logs_dir']]:
            for file_path in directory.glob(pattern):
                try:
                    file_path.unlink()
                except Exception:
                    pass
    
    def get_test_data_path(self, filename: str) -> Path:
        """Get path to test data file"""
        return TEST_CONFIG['test_data_dir'] / filename
    
    def get_report_path(self, filename: str) -> Path:
        """Get path to report file"""
        return TEST_CONFIG['reports_dir'] / filename
    
    def get_log_path(self, filename: str) -> Path:
        """Get path to log file"""
        return TEST_CONFIG['logs_dir'] / filename

# Global test environment instance
test_env = TestEnvironment()

# Export commonly used items
__all__ = [
    'TEST_CONFIG',
    'TEST_DATA', 
    'SECURITY_PAYLOADS',
    'TestResult',
    'TestUtilities',
    'MockServices',
    'TestEnvironment',
    'test_env'
]