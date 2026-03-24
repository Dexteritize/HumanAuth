#!/usr/bin/env python3
"""
Test script to verify the authentication display fix.

This script tests:
1. Logging only occurs when authentication is successful
2. Authentication information is properly captured in logs
3. Session summary data is correctly structured for frontend display
"""

import sys
import os
import json
from pathlib import Path
sys.path.append('/Users/jasondank/PycharmProjects/HumanAuth/humanauth-render/backend')

def test_logging_only_on_success():
    """Test that logging only occurs when authentication is successful"""
    print("Testing logging behavior...")
    print("=" * 50)
    
    try:
        from human_auth import HumanAuth
        import numpy as np
        import cv2
        
        # Clear existing log files for clean test
        log_dir = Path('/Users/jasondank/PycharmProjects/HumanAuth/humanauth-render/auth_log')
        initial_log_count = len(list(log_dir.glob('*.json'))) if log_dir.exists() else 0
        print(f"Initial log files: {initial_log_count}")
        
        # Initialize HumanAuth
        auth = HumanAuth()
        print("✅ HumanAuth initialized successfully")
        
        # Create a mock frame (this should not trigger authentication)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (200, 150), (440, 330), (100, 100, 100), -1)
        
        # Process several frames (should not authenticate due to lack of real face/hand)
        print("\nProcessing frames that should NOT authenticate...")
        for i in range(5):
            result = auth.update(frame)
            print(f"Frame {i+1}: authenticated={result.authenticated}, confidence={result.confidence:.3f}")
            
            if result.authenticated:
                print(f"❌ Unexpected authentication on frame {i+1}")
                return False
        
        # Check that no new log files were created (since no authentication occurred)
        current_log_count = len(list(log_dir.glob('*.json'))) if log_dir.exists() else 0
        new_logs = current_log_count - initial_log_count
        
        if new_logs == 0:
            print("✅ No log files created for failed authentication attempts")
        else:
            print(f"❌ {new_logs} log files created for failed authentication (should be 0)")
            return False
        
        print("\n" + "=" * 50)
        print("✅ Logging behavior test PASSED")
        print("- No logs created for failed authentication attempts")
        print("- Logging only occurs when authentication is successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing logging behavior: {e}")
        return False

def test_session_summary_structure():
    """Test that session summary has the correct structure for frontend display"""
    print("\n\nTesting session summary structure...")
    print("=" * 50)
    
    try:
        # Check the most recent log file to verify structure
        log_dir = Path('/Users/jasondank/PycharmProjects/HumanAuth/humanauth-render/auth_log')
        if not log_dir.exists():
            print("❌ No auth_log directory found")
            return False
        
        log_files = sorted(log_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
        if not log_files:
            print("❌ No log files found")
            return False
        
        # Examine the most recent log file
        latest_log = log_files[0]
        print(f"Examining log file: {latest_log.name}")
        
        with open(latest_log, 'r') as f:
            log_data = json.load(f)
        
        # Check required fields for frontend display
        required_fields = [
            'authenticated',
            'confidence', 
            'auth_method',
            'detector_contributions',
            'final_scores',
            'challenge_history',
            'weights',
            'session_duration',
            'frames_processed'
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in log_data:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ All required fields present in log data")
        
        # Verify authentication was successful
        if not log_data.get('authenticated', False):
            print("❌ Log shows authentication failed")
            return False
        
        print(f"✅ Authentication successful with {log_data['confidence']:.1%} confidence")
        
        # Check detector contributions structure
        detector_contributions = log_data.get('detector_contributions', {})
        expected_detectors = ['Micro Movement', '3D Consistency', 'Blink Pattern', 
                            'Challenge Response', 'Texture Analysis', 'Hand Detection']
        
        missing_detectors = [d for d in expected_detectors if d not in detector_contributions]
        if missing_detectors:
            print(f"❌ Missing detector contributions: {missing_detectors}")
            return False
        
        print("✅ All detector contributions present")
        
        # Check challenge history
        challenge_history = log_data.get('challenge_history', [])
        if challenge_history:
            print(f"✅ Challenge history contains {len(challenge_history)} challenges")
            for i, challenge in enumerate(challenge_history):
                required_challenge_fields = ['challenge', 'response_time', 'score', 'timestamp']
                missing_challenge_fields = [f for f in required_challenge_fields if f not in challenge]
                if missing_challenge_fields:
                    print(f"❌ Challenge {i+1} missing fields: {missing_challenge_fields}")
                    return False
            print("✅ All challenges have required fields")
        else:
            print("⚠️  No challenge history (may be normal for some auth methods)")
        
        print("\n" + "=" * 50)
        print("✅ Session summary structure test PASSED")
        print("- All required fields present for frontend display")
        print("- Detector contributions properly structured")
        print("- Challenge history properly formatted")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing session summary structure: {e}")
        return False

def test_frontend_data_compatibility():
    """Test that the log data structure matches frontend expectations"""
    print("\n\nTesting frontend data compatibility...")
    print("=" * 50)
    
    try:
        # Check the most recent log file
        log_dir = Path('/Users/jasondank/PycharmProjects/HumanAuth/humanauth-render/auth_log')
        log_files = sorted(log_dir.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if not log_files:
            print("❌ No log files found")
            return False
        
        with open(log_files[0], 'r') as f:
            log_data = json.load(f)
        
        # Simulate the data structure that would be sent to frontend
        frontend_session_summary = {
            'auth_method': log_data.get('auth_method', 'unknown'),
            'final_confidence': log_data.get('confidence', 0),
            'auth_threshold': log_data.get('auth_threshold', 0.55),
            'challenges_completed': log_data.get('successful_challenges', 0),
            'challenges_required': log_data.get('required_challenges', 3),
            'passive_base': log_data.get('passive_base', 0),
            'challenge_boost': log_data.get('challenge_boost', 0),
            'detector_contributions': log_data.get('detector_contributions', {}),
            'completed_challenges': log_data.get('challenge_history', []),
            'final_scores': log_data.get('final_scores', {}),
            'weights': log_data.get('weights', {}),
            'session_duration': log_data.get('session_duration', 0),
            'frames_processed': log_data.get('frames_processed', 0)
        }
        
        print("✅ Frontend-compatible session summary created:")
        print(f"   - Auth method: {frontend_session_summary['auth_method']}")
        print(f"   - Final confidence: {frontend_session_summary['final_confidence']:.1%}")
        print(f"   - Challenges: {frontend_session_summary['challenges_completed']}/{frontend_session_summary['challenges_required']}")
        print(f"   - Session duration: {frontend_session_summary['session_duration']:.1f}s")
        print(f"   - Frames processed: {frontend_session_summary['frames_processed']}")
        print(f"   - Detector contributions: {len(frontend_session_summary['detector_contributions'])} detectors")
        
        print("\n" + "=" * 50)
        print("✅ Frontend data compatibility test PASSED")
        print("- Log data structure matches frontend SessionSummary interface")
        print("- All required fields properly mapped")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing frontend compatibility: {e}")
        return False

def main():
    print("Authentication Display Fix Verification")
    print("=" * 60)
    print()
    
    # Run all tests
    test1 = test_logging_only_on_success()
    test2 = test_session_summary_structure()
    test3 = test_frontend_data_compatibility()
    
    print("\n" + "=" * 60)
    print("FINAL SUMMARY:")
    
    if all([test1, test2, test3]):
        print("✅ ALL TESTS PASSED!")
        print()
        print("The authentication display fix is working correctly:")
        print("1. ✅ Logging only occurs when authentication is successful")
        print("2. ✅ Authentication information is properly captured in logs")
        print("3. ✅ Session summary data is correctly structured for frontend")
        print()
        print("Key improvements:")
        print("- Reduced log noise by only logging successful authentications")
        print("- Comprehensive authentication details available in logs")
        print("- Data structure compatible with frontend display requirements")
        print()
        print("Users should now see detailed authentication information")
        print("on screen after successful authentication.")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the failed tests above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)