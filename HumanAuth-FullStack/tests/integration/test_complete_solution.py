#!/usr/bin/env python3
"""
Test script to verify the complete solution for the authentication issues:
1. Auth logging functionality
2. Overlay opacity improvements
3. Authentication summary display
"""

import sys
import os
import json
from pathlib import Path
sys.path.append('/HumanAuth-FullStack/backend')

def test_auth_log_folder():
    """Test that the auth_log folder exists"""
    print("Testing auth_log folder creation...")
    log_dir = Path('/HumanAuth-FullStack/auth_log')
    
    if log_dir.exists() and log_dir.is_dir():
        print("✅ auth_log folder exists")
        return True
    else:
        print("❌ auth_log folder does not exist")
        return False

def test_logging_functionality():
    """Test the logging functionality by running a mock authentication"""
    print("\nTesting authentication logging functionality...")
    
    try:
        from human_auth import HumanAuth
        import numpy as np
        import cv2
        
        # Initialize HumanAuth
        auth = HumanAuth()
        print("✅ HumanAuth initialized successfully")
        
        # Create a mock frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(frame, (200, 150), (440, 330), (100, 100, 100), -1)
        
        # Process one frame to trigger logging
        result = auth.update(frame)
        print(f"✅ Frame processed - Authenticated: {result.authenticated}, Confidence: {result.confidence:.3f}")
        
        # Check if log file was created
        log_dir = Path('/HumanAuth-FullStack/auth_log')
        log_files = list(log_dir.glob('auth_log_*.json'))
        
        if log_files:
            print(f"✅ Log file created: {log_files[-1].name}")
            
            # Verify log content
            with open(log_files[-1], 'r') as f:
                log_data = json.load(f)
            
            required_fields = ['timestamp', 'authenticated', 'confidence', 'session_duration', 
                             'frames_processed', 'successful_challenges', 'weights']
            
            missing_fields = [field for field in required_fields if field not in log_data]
            if missing_fields:
                print(f"❌ Missing log fields: {missing_fields}")
                return False
            else:
                print("✅ Log file contains all required fields")
                print(f"   - Timestamp: {log_data['timestamp']}")
                print(f"   - Authenticated: {log_data['authenticated']}")
                print(f"   - Confidence: {log_data['confidence']:.3f}")
                print(f"   - Challenges: {log_data['successful_challenges']}/{log_data['required_challenges']}")
                return True
        else:
            print("❌ No log files found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing logging functionality: {e}")
        return False

def test_overlay_opacity_improvements():
    """Test that overlay opacity improvements are in place"""
    print("\nTesting overlay opacity improvements...")
    
    try:
        # Check TypeScript component for increased opacity values
        ts_file = Path('/HumanAuth-FullStack/frontend/src/app/auth-page/auth-page.component.ts')
        
        if not ts_file.exists():
            print("❌ TypeScript component file not found")
            return False
        
        with open(ts_file, 'r') as f:
            content = f.read()
        
        # Check for increased opacity values
        opacity_checks = [
            ('rgba(0, 0, 0, 0.65)', 'Base dim overlay increased to 0.65'),
            ('rgba(0, 0, 0, 0.75)', 'Vignette overlay increased to 0.75'),
            ('rgba(0, 255, 170, 0.55)', 'Glow shadow increased to 0.55'),
            ('rgba(255, 215, 120, 0.45)', 'Glow shadow increased to 0.45'),
            ('rgba(0, 255, 200, 0.55)', 'Border opacity increased to 0.55'),
            ('rgba(255,255,255,0.35)', 'Stroke style increased to 0.35')
        ]
        
        all_found = True
        for opacity_value, description in opacity_checks:
            if opacity_value in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - not found")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Error testing overlay opacity: {e}")
        return False

def test_session_summary_display():
    """Test that session summary display is properly configured"""
    print("\nTesting session summary display configuration...")
    
    try:
        # Check HTML template for session summary display
        html_file = Path('/HumanAuth-FullStack/frontend/src/app/auth-page/auth-page.component.html')
        
        if not html_file.exists():
            print("❌ HTML template file not found")
            return False
        
        with open(html_file, 'r') as f:
            content = f.read()
        
        # Check for session summary display elements
        summary_checks = [
            ('*ngIf="sessionSummary && result?.authenticated"', 'Session summary display condition'),
            ('Authentication Summary', 'Authentication summary title'),
            ('sessionSummary.final_confidence', 'Final confidence display'),
            ('getDetectorEntries()', 'Detector contributions'),
            ('sessionSummary.completed_challenges', 'Challenge history')
        ]
        
        all_found = True
        for check_value, description in summary_checks:
            if check_value in content:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} - not found")
                all_found = False
        
        return all_found
        
    except Exception as e:
        print(f"❌ Error testing session summary display: {e}")
        return False

def main():
    print("Testing Complete Solution for Authentication Issues")
    print("=" * 60)
    
    # Run all tests
    test1 = test_auth_log_folder()
    test2 = test_logging_functionality()
    test3 = test_overlay_opacity_improvements()
    test4 = test_session_summary_display()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    
    if all([test1, test2, test3, test4]):
        print("✅ ALL TESTS PASSED!")
        print("\nThe complete solution addresses all issues:")
        print("1. ✅ Auth logging: Authentication decisions are now logged to JSON files")
        print("2. ✅ Overlay opacity: Screen overlays are much more opaque and visible")
        print("3. ✅ Session summary: Display configuration is properly set up")
        print("\nFeatures implemented:")
        print("- auth_log folder created in HumanAuth-FullStack directory")
        print("- Comprehensive JSON logging of authentication decisions")
        print("- Increased overlay opacity for better visibility")
        print("- Base dim: 0.38 → 0.65, Vignette: 0.55 → 0.75")
        print("- Enhanced glow, border, and stroke opacity")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the failed tests above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)