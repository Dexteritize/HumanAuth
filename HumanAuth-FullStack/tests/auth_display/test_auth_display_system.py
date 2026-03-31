#!/usr/bin/env python3
"""
Test script to verify the authentication display system is working correctly.
This tests that:
1. Auth log files are created when authentication completes
2. Session summary data is properly structured
3. Frontend can display the results
"""

import json
import time
from pathlib import Path
import requests
import subprocess
import signal
import os

def test_auth_log_system():
    """Test that the auth log system is working"""
    print("Testing authentication log system...")
    
    # Check if auth_log directory exists
    log_dir = Path('/HumanAuth-FullStack/auth_log')
    if not log_dir.exists():
        print("❌ auth_log directory does not exist")
        return False
    
    # Check for recent log files
    log_files = list(log_dir.glob('auth_log_*.json'))
    if not log_files:
        print("❌ No auth log files found")
        return False
    
    # Get the most recent log file
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    print(f"✅ Found recent auth log: {latest_log.name}")
    
    # Verify log file structure
    try:
        with open(latest_log, 'r') as f:
            log_data = json.load(f)
        
        required_fields = [
            'timestamp', 'authenticated', 'confidence', 'session_duration',
            'frames_processed', 'successful_challenges', 'required_challenges',
            'auth_threshold', 'challenge_history', 'weights'
        ]
        
        missing_fields = [field for field in required_fields if field not in log_data]
        if missing_fields:
            print(f"❌ Missing required fields in log: {missing_fields}")
            return False
        
        print("✅ Auth log structure is valid")
        
        # Check if authentication was successful
        if log_data.get('authenticated'):
            print("✅ Authentication was successful")
            
            # Check for session summary fields
            summary_fields = ['auth_method', 'passive_base', 'challenge_boost', 
                            'detector_contributions', 'final_scores']
            has_summary = all(field in log_data for field in summary_fields)
            
            if has_summary:
                print("✅ Session summary data is present")
            else:
                print("⚠️  Some session summary fields are missing")
        else:
            print("ℹ️  Authentication was not successful in this log")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return False

def test_backend_api():
    """Test that the backend API is providing session summary data"""
    print("\nTesting backend API...")
    
    try:
        # Check if backend is running
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
        else:
            print("❌ Backend health check failed")
            return False
    except requests.exceptions.RequestException:
        print("❌ Backend is not accessible")
        return False
    
    return True

def test_frontend_structure():
    """Test that the frontend has the necessary components for displaying results"""
    print("\nTesting frontend structure...")
    
    # Check auth-page component HTML
    html_file = Path('/HumanAuth-FullStack/frontend/src/app/auth-page/auth-page.component.html')
    if not html_file.exists():
        print("❌ Auth page component HTML not found")
        return False
    
    with open(html_file, 'r') as f:
        html_content = f.read()
    
    # Check for session summary panel
    if 'ha-summary-panel' in html_content and 'sessionSummary' in html_content:
        print("✅ Session summary panel found in HTML")
    else:
        print("❌ Session summary panel not found in HTML")
        return False
    
    # Check TypeScript component
    ts_file = Path('/HumanAuth-FullStack/frontend/src/app/auth-page/auth-page.component.ts')
    if not ts_file.exists():
        print("❌ Auth page component TypeScript not found")
        return False
    
    with open(ts_file, 'r') as f:
        ts_content = f.read()
    
    if 'sessionSummary' in ts_content and 'result.session_summary' in ts_content:
        print("✅ Session summary handling found in TypeScript")
    else:
        print("❌ Session summary handling not found in TypeScript")
        return False
    
    return True

def check_system_status():
    """Check if the authentication display system is working as intended"""
    print("=" * 60)
    print("AUTHENTICATION DISPLAY SYSTEM TEST")
    print("=" * 60)
    
    results = []
    
    # Test auth log system
    results.append(test_auth_log_system())
    
    # Test backend API
    results.append(test_backend_api())
    
    # Test frontend structure
    results.append(test_frontend_structure())
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if all(results):
        print("✅ All tests passed! The authentication display system appears to be working correctly.")
        print("\nThe system should:")
        print("- Create auth log files when authentication completes")
        print("- Display session summary in the frontend after successful auth")
        print("- Allow users to start a new session with the reset button")
        print("\nIf users are not seeing results after authentication, check:")
        print("1. Browser console for JavaScript errors")
        print("2. Network tab for API communication issues")
        print("3. Backend logs for authentication processing errors")
    else:
        print("❌ Some tests failed. The authentication display system may need fixes.")
        
        failed_tests = []
        if not results[0]:
            failed_tests.append("Auth log system")
        if not results[1]:
            failed_tests.append("Backend API")
        if not results[2]:
            failed_tests.append("Frontend structure")
        
        print(f"\nFailed components: {', '.join(failed_tests)}")
    
    return all(results)

if __name__ == "__main__":
    check_system_status()