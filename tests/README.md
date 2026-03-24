# HumanAuth Testing Suite

This directory contains all test files for the HumanAuth project, organized by category for better maintainability.

## Directory Structure

### `/auth_display/`
Tests specifically related to authentication display functionality:
- `test_auth_display_system.py` - Tests the authentication display system components
- `test_auth_display_fix.py` - Tests for authentication display fixes
- `test_enhanced_display.py` - Tests for enhanced display improvements

### `/integration/`
Integration tests that test multiple components working together:
- `test_auth_issue.py` - Tests for authentication issue fixes
- `test_complete_solution.py` - Complete solution integration tests

### `/verification/`
Verification scripts for manual and automated validation:
- `verify_auth_fix.py` - Verification script for authentication fixes
- `verify_auth_display.py` - Verification script for display functionality

## Running Tests

### From Project Root
```bash
# Run all auth display tests
python tests/auth_display/test_auth_display_system.py
python tests/auth_display/test_enhanced_display.py

# Run integration tests
python tests/integration/test_auth_issue.py
python tests/integration/test_complete_solution.py

# Run verification scripts
python tests/verification/verify_auth_fix.py
python tests/verification/verify_auth_display.py
```

### From Tests Directory
```bash
cd tests

# Run specific category tests
python auth_display/test_auth_display_system.py
python integration/test_auth_issue.py
python verification/verify_auth_fix.py
```

## Test Categories

- **Auth Display Tests**: Focus on UI components, session summaries, and result display
- **Integration Tests**: Test complete authentication workflows and system interactions
- **Verification Scripts**: Manual and automated validation of fixes and features

## Adding New Tests

When adding new tests, place them in the appropriate category directory:
- Authentication display related → `auth_display/`
- Multi-component integration → `integration/`
- Verification and validation → `verification/`

Follow the naming convention: `test_*.py` for automated tests, `verify_*.py` for verification scripts.