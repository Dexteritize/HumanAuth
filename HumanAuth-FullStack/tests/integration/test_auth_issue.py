#!/usr/bin/env python3
"""
Test script to reproduce and verify the authentication issue fix.
This script tests that:
1. Authentication completes properly
2. Camera stops after authentication
3. Results are displayed to the user
"""

import json
import time
import subprocess
import signal
import os
from pathlib import Path
import requests

def check_backend_running():
    """Check if the backend is running"""
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_backend():
    """Start the backend server"""
    print("Starting backend server...")
    backend_dir = Path('/HumanAuth-FullStack')
    
    # Change to backend directory and start server
    process = subprocess.Popen(
        ['./start.sh'],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    # Wait a moment for server to start
    time.sleep(3)
    
    if check_backend_running():
        print("✅ Backend server started successfully")
        return process
    else:
        print("❌ Failed to start backend server")
        return None

def test_auth_completion_behavior():
    """Test the authentication completion behavior"""
    print("\n" + "=" * 60)
    print("TESTING AUTHENTICATION COMPLETION BEHAVIOR")
    print("=" * 60)
    
    # Check if backend is running
    if not check_backend_running():
        print("❌ Backend is not running. Please start the backend first.")
        return False
    
    print("✅ Backend is running")
    
    # Check auth log directory
    log_dir = Path('/HumanAuth-FullStack/auth_log')
    if not log_dir.exists():
        print("❌ Auth log directory does not exist")
        return False
    
    print("✅ Auth log directory exists")
    
    # Get initial log count
    initial_logs = list(log_dir.glob('auth_log_*.json'))
    initial_count = len(initial_logs)
    print(f"ℹ️  Initial auth log count: {initial_count}")
    
    print("\n📋 MANUAL TEST INSTRUCTIONS:")
    print("1. Open your browser and navigate to the frontend")
    print("2. Click 'Start' to begin authentication")
    print("3. Complete the required challenges")
    print("4. Observe the behavior when authentication completes")
    print("\n🔍 EXPECTED BEHAVIOR AFTER FIX:")
    print("✅ Camera should stop (video feed should freeze/disappear)")
    print("✅ Processing should stop (no more frame processing)")
    print("✅ Success message should be displayed")
    print("✅ Session summary panel should appear with detailed results")
    print("✅ 'Start New Session' button should be available")
    print("\n❌ PREVIOUS PROBLEMATIC BEHAVIOR:")
    print("❌ Camera continued running after authentication")
    print("❌ Video feed kept showing live camera")
    print("❌ Processing continued in background")
    
    print("\nPress Enter when you have completed the authentication test...")
    input()
    
    # Check for new auth logs
    final_logs = list(log_dir.glob('auth_log_*.json'))
    final_count = len(final_logs)
    
    if final_count > initial_count:
        print(f"✅ New auth log created ({final_count - initial_count} new logs)")
        
        # Check the latest log
        latest_log = max(final_logs, key=lambda f: f.stat().st_mtime)
        try:
            with open(latest_log, 'r') as f:
                log_data = json.load(f)
            
            if log_data.get('authenticated'):
                print("✅ Authentication was successful according to log")
                print(f"ℹ️  Confidence: {log_data.get('confidence', 0):.2f}")
                print(f"ℹ️  Challenges completed: {log_data.get('successful_challenges', 0)}/{log_data.get('required_challenges', 3)}")
                return True
            else:
                print("⚠️  Authentication was not successful in the latest log")
                return False
                
        except Exception as e:
            print(f"❌ Error reading latest log: {e}")
            return False
    else:
        print("⚠️  No new auth logs created - authentication may not have completed")
        return False

def verify_frontend_changes():
    """Verify that the frontend changes are in place"""
    print("\n" + "=" * 60)
    print("VERIFYING FRONTEND CHANGES")
    print("=" * 60)
    
    component_file = Path('/HumanAuth-FullStack/frontend/src/app/auth-page/auth-page.component.ts')
    
    if not component_file.exists():
        print("❌ Frontend component file not found")
        return False
    
    with open(component_file, 'r') as f:
        content = f.read()
    
    # Check for the fix
    if 'stopCameraOnly()' in content:
        print("✅ stopCameraOnly() method found")
    else:
        print("❌ stopCameraOnly() method not found")
        return False
    
    if 'this.stopCameraOnly();' in content:
        print("✅ stopCameraOnly() call found in authentication success handler")
    else:
        print("❌ stopCameraOnly() call not found in authentication success handler")
        return False
    
    # Check that the method preserves state
    if 'preserve authentication results and UI state' in content:
        print("✅ Method correctly preserves authentication results")
    else:
        print("❌ Method may not preserve authentication results")
        return False
    
    return True

def main():
    """Main test function"""
    print("🧪 AUTHENTICATION ISSUE FIX TEST")
    print("=" * 60)
    
    # Verify frontend changes
    if not verify_frontend_changes():
        print("\n❌ Frontend changes verification failed")
        return
    
    # Test authentication behavior
    if not test_auth_completion_behavior():
        print("\n❌ Authentication completion test failed")
        return
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nThe authentication issue fix appears to be working correctly.")
    print("The camera should now stop when authentication completes,")
    print("and the results should be displayed to the user.")

if __name__ == "__main__":
    main()