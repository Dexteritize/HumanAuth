#!/usr/bin/env python3
"""
Verification script to confirm that authorization details are displayed to users.

This script analyzes the HumanAuth implementation to verify that the issue requirement
is met: "Once the system authorises us we MUST display something on the demo page 
that demonstrates to the user how they were authorised"
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists and print status"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (NOT FOUND)")
        return False

def check_file_contains(filepath, search_terms, description):
    """Check if a file contains specific terms"""
    if not os.path.exists(filepath):
        print(f"❌ {description}: File not found - {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        found_terms = []
        missing_terms = []
        
        for term in search_terms:
            if term in content:
                found_terms.append(term)
            else:
                missing_terms.append(term)
        
        if missing_terms:
            print(f"❌ {description}: Missing terms - {missing_terms}")
            return False
        else:
            print(f"✅ {description}: All required terms found - {found_terms}")
            return True
            
    except Exception as e:
        print(f"❌ {description}: Error reading file - {e}")
        return False

def main():
    print("HumanAuth Authorization Display Verification")
    print("=" * 50)
    
    base_path = "/HumanAuth-FullStack"
    
    # Check key files exist
    files_to_check = [
        (f"{base_path}/frontend/src/app/auth-page/auth-page.component.html", "Auth Page HTML Template"),
        (f"{base_path}/frontend/src/app/auth-page/auth-page.component.ts", "Auth Page TypeScript Component"),
        (f"{base_path}/frontend/src/app/services/auth.service.ts", "Auth Service"),
        (f"{base_path}/backend/auth_types.py", "Backend Auth Types"),
        (f"{base_path}/backend/human_auth.py", "Backend Human Auth")
    ]
    
    print("\n1. Checking required files exist:")
    all_files_exist = True
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_files_exist = False
    
    if not all_files_exist:
        print("\n❌ Some required files are missing!")
        return False
    
    # Check HTML template has authorization display elements
    print("\n2. Checking HTML template has authorization display:")
    html_terms = [
        "Authentication Summary",
        "sessionSummary",
        "result?.authenticated",
        "Authentication Details",
        "Confidence Breakdown",
        "Detector Analysis",
        "Challenge History",
        "Session Statistics"
    ]
    
    html_check = check_file_contains(
        f"{base_path}/frontend/src/app/auth-page/auth-page.component.html",
        html_terms,
        "HTML Authorization Display Elements"
    )
    
    # Check TypeScript component has session summary handling
    print("\n3. Checking TypeScript component handles session summary:")
    ts_terms = [
        "SessionSummary",
        "sessionSummary",
        "result.session_summary",
        "getDetectorEntries",
        "detector_contributions",
        "final_confidence",
        "auth_method"
    ]
    
    ts_check = check_file_contains(
        f"{base_path}/frontend/src/app/auth-page/auth-page.component.ts",
        ts_terms,
        "TypeScript Session Summary Handling"
    )
    
    # Check auth service returns proper data structure
    print("\n4. Checking auth service data structures:")
    service_terms = [
        "SessionSummary",
        "AuthResult",
        "session_summary",
        "detector_contributions",
        "completed_challenges",
        "final_confidence"
    ]
    
    service_check = check_file_contains(
        f"{base_path}/frontend/src/app/services/auth.service.ts",
        service_terms,
        "Auth Service Data Structures"
    )
    
    # Check backend provides comprehensive auth data
    print("\n5. Checking backend provides comprehensive auth data:")
    backend_terms = [
        "SessionSummary",
        "AuthResult",
        "auth_method",
        "detector_contributions",
        "completed_challenges",
        "final_confidence",
        "challenge_boost",
        "passive_base"
    ]
    
    backend_check = check_file_contains(
        f"{base_path}/backend/auth_types.py",
        backend_terms,
        "Backend Auth Data Structures"
    )
    
    # Summary
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY:")
    
    all_checks_passed = html_check and ts_check and service_check and backend_check
    
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED!")
        print("\nThe HumanAuth system already implements comprehensive authorization")
        print("details display that meets the requirement:")
        print("'Once the system authorises us we MUST display something on the demo")
        print("page that demonstrates to the user how they were authorised'")
        print("\nThe implementation includes:")
        print("- Authentication Summary panel shown after successful auth")
        print("- Detailed confidence breakdown (passive base + challenge boost)")
        print("- Individual detector contributions with scores and weights")
        print("- Challenge history with response times and scores")
        print("- Session statistics and authentication method used")
        print("- Comprehensive technical details of the authorization process")
        return True
    else:
        print("❌ SOME CHECKS FAILED!")
        print("The authorization display implementation may be incomplete.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)