#!/usr/bin/env python3
"""
Comprehensive test suite for auth-page component functionality.
Tests the Angular component behavior, state management, and UI interactions.
"""

import unittest
import json
import re
from pathlib import Path
import sys
import os

class TestAuthPageComponent(unittest.TestCase):
    """Test cases for auth-page component structure and functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.component_path = Path(__file__).parent.parent.parent / 'humanauth-render' / 'frontend' / 'src' / 'app' / 'auth-page'
        self.ts_file = self.component_path / 'auth-page.component.ts'
        self.html_file = self.component_path / 'auth-page.component.html'
        self.scss_file = self.component_path / 'auth-page.component.scss'
    
    def test_component_files_exist(self):
        """Test that all component files exist"""
        self.assertTrue(self.ts_file.exists(), "TypeScript component file should exist")
        self.assertTrue(self.html_file.exists(), "HTML template file should exist")
        self.assertTrue(self.scss_file.exists(), "SCSS style file should exist")
    
    def test_typescript_component_structure(self):
        """Test TypeScript component structure and key methods"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test component decorator
        self.assertIn('@Component', content, "Component should have @Component decorator")
        self.assertIn('selector:', content, "Component should have selector")
        self.assertIn('templateUrl:', content, "Component should have templateUrl")
        self.assertIn('styleUrls:', content, "Component should have styleUrls")
        
        # Test class definition
        self.assertIn('export class AuthPageComponent', content, "Should export AuthPageComponent class")
        self.assertIn('implements OnDestroy', content, "Should implement OnDestroy")
        
        # Test key properties
        key_properties = [
            'running', 'result', 'error', 'uiState', 'sessionSummary'
        ]
        for prop in key_properties:
            self.assertIn(prop, content, f"Should have {prop} property")
        
        # Test key methods
        key_methods = [
            'start()', 'stop()', 'reload()', 'ngOnDestroy()'
        ]
        for method in key_methods:
            self.assertIn(method, content, f"Should have {method} method")
    
    def test_component_imports(self):
        """Test that component has necessary imports"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test Angular imports
        angular_imports = [
            'Component', 'ElementRef', 'ViewChild', 'OnDestroy', 'NgZone'
        ]
        for imp in angular_imports:
            self.assertIn(imp, content, f"Should import {imp} from Angular")
        
        # Test service imports
        service_imports = ['CameraService', 'AuthService']
        for service in service_imports:
            self.assertIn(service, content, f"Should import {service}")
    
    def test_component_lifecycle_methods(self):
        """Test component lifecycle methods"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test ngOnDestroy implementation
        self.assertIn('ngOnDestroy()', content, "Should implement ngOnDestroy")
        
        # Test cleanup in ngOnDestroy
        cleanup_patterns = ['stop()', 'removeEventListener', 'cancelAnimationFrame']
        ngOnDestroy_match = re.search(r'ngOnDestroy\(\)\s*{([^}]+)}', content, re.DOTALL)
        if ngOnDestroy_match:
            ngOnDestroy_content = ngOnDestroy_match.group(1)
            # At least one cleanup pattern should be present
            has_cleanup = any(pattern in ngOnDestroy_content for pattern in cleanup_patterns)
            self.assertTrue(has_cleanup, "ngOnDestroy should perform cleanup")
    
    def test_state_management(self):
        """Test component state management"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test UI state enum
        self.assertIn('enum UiState', content, "Should define UiState enum")
        
        # Test state values
        ui_states = ['Idle', 'Starting', 'Running', 'Success', 'Error', 'Stopped']
        for state in ui_states:
            self.assertIn(state, content, f"Should have {state} state")
        
        # Test state management methods
        state_methods = ['setState', 'canStart', 'canStop', 'canReload']
        for method in state_methods:
            self.assertIn(method, content, f"Should have {method} for state management")
    
    def test_camera_integration(self):
        """Test camera service integration"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test camera service injection
        self.assertIn('CameraService', content, "Should inject CameraService")
        
        # Test camera methods usage
        camera_methods = ['start', 'stop', 'capture']
        for method in camera_methods:
            # Look for this.cam.method() pattern
            pattern = f'this\.cam\.{method}'
            self.assertTrue(re.search(pattern, content), f"Should use camera {method} method")
    
    def test_auth_service_integration(self):
        """Test authentication service integration"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test auth service injection
        self.assertIn('AuthService', content, "Should inject AuthService")
        
        # Test auth methods usage
        auth_methods = ['initialize', 'startAuth', 'processFrame', 'resetAuth']
        for method in auth_methods:
            # Look for this.auth.method() pattern
            pattern = f'this\.auth\.{method}'
            self.assertTrue(re.search(pattern, content), f"Should use auth {method} method")
    
    def test_canvas_drawing_functionality(self):
        """Test canvas drawing and visualization functionality"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test canvas references
        self.assertIn('@ViewChild("canvas")', content, "Should have canvas ViewChild")
        
        # Test drawing methods
        drawing_methods = [
            'drawVisualIndicators', 'drawFaceLandmarks', 'drawHandLandmarks', 
            'drawHud', 'drawMetricsScores'
        ]
        for method in drawing_methods:
            self.assertIn(method, content, f"Should have {method} drawing method")
        
        # Test canvas context usage
        canvas_patterns = ['getContext', 'clearRect', 'fillRect', 'strokeRect']
        for pattern in canvas_patterns:
            self.assertIn(pattern, content, f"Should use canvas {pattern}")

class TestAuthPageTemplate(unittest.TestCase):
    """Test cases for auth-page component HTML template"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.html_file = Path(__file__).parent.parent.parent / 'humanauth-render' / 'frontend' / 'src' / 'app' / 'auth-page' / 'auth-page.component.html'
    
    def test_template_structure(self):
        """Test HTML template structure"""
        if not self.html_file.exists():
            self.skipTest("HTML template file not found")
        
        with open(self.html_file, 'r') as f:
            content = f.read()
        
        # Test main container
        self.assertIn('ha-panel', content, "Should have main panel container")
        
        # Test video and canvas elements
        self.assertIn('<video', content, "Should have video element")
        self.assertIn('<canvas', content, "Should have canvas element")
        self.assertIn('#video', content, "Should have video template reference")
        self.assertIn('#canvas', content, "Should have canvas template reference")
    
    def test_control_buttons(self):
        """Test control button elements"""
        if not self.html_file.exists():
            self.skipTest("HTML template file not found")
        
        with open(self.html_file, 'r') as f:
            content = f.read()
        
        # Test button elements
        button_actions = ['start()', 'stop()', 'reload()']
        for action in button_actions:
            self.assertIn(f'(click)="{action}"', content, f"Should have {action} button")
        
        # Test button states
        button_states = ['[disabled]="!canStart"', '[disabled]="!canStop"', '[disabled]="!canReload"']
        for state in button_states:
            self.assertIn(state, content, f"Should have button state: {state}")
    
    def test_session_summary_panel(self):
        """Test session summary panel in template"""
        if not self.html_file.exists():
            self.skipTest("HTML template file not found")
        
        with open(self.html_file, 'r') as f:
            content = f.read()
        
        # Test session summary panel
        self.assertIn('ha-summary-panel', content, "Should have session summary panel")
        self.assertIn('*ngIf="sessionSummary', content, "Should conditionally show session summary")
        
        # Test summary content
        summary_elements = [
            'ha-summary-title', 'ha-quick-stats', 'ha-detector-list', 'ha-challenge-list'
        ]
        for element in summary_elements:
            self.assertIn(element, content, f"Should have {element} in summary")
    
    def test_angular_directives(self):
        """Test Angular directive usage"""
        if not self.html_file.exists():
            self.skipTest("HTML template file not found")
        
        with open(self.html_file, 'r') as f:
            content = f.read()
        
        # Test structural directives
        structural_directives = ['*ngIf', '*ngFor']
        for directive in structural_directives:
            self.assertIn(directive, content, f"Should use {directive} directive")
        
        # Test property binding
        property_bindings = ['[disabled]', '[class]', '[style']
        for binding in property_bindings:
            self.assertIn(binding, content, f"Should use {binding} property binding")
        
        # Test event binding
        event_bindings = ['(click)', '(change)']
        for binding in event_bindings:
            self.assertIn(binding, content, f"Should use {binding} event binding")

class TestAuthPageStyles(unittest.TestCase):
    """Test cases for auth-page component SCSS styles"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scss_file = Path(__file__).parent.parent.parent / 'humanauth-render' / 'frontend' / 'src' / 'app' / 'auth-page' / 'auth-page.component.scss'
    
    def test_style_structure(self):
        """Test SCSS style structure"""
        if not self.scss_file.exists():
            self.skipTest("SCSS file not found")
        
        with open(self.scss_file, 'r') as f:
            content = f.read()
        
        # Test main component styles
        main_selectors = ['.ha-panel', '.ha-stage', '.ha-video', '.ha-canvas']
        for selector in main_selectors:
            self.assertIn(selector, content, f"Should have {selector} styles")
    
    def test_responsive_design(self):
        """Test responsive design elements"""
        if not self.scss_file.exists():
            self.skipTest("SCSS file not found")
        
        with open(self.scss_file, 'r') as f:
            content = f.read()
        
        # Test responsive utilities
        responsive_elements = ['clamp(', '@media', 'vw', 'vh']
        for element in responsive_elements:
            self.assertIn(element, content, f"Should use responsive {element}")
    
    def test_animation_styles(self):
        """Test animation and transition styles"""
        if not self.scss_file.exists():
            self.skipTest("SCSS file not found")
        
        with open(self.scss_file, 'r') as f:
            content = f.read()
        
        # Test animation properties
        animation_props = ['transition:', 'transform:', 'animation:']
        has_animations = any(prop in content for prop in animation_props)
        self.assertTrue(has_animations, "Should have animation/transition styles")

class TestComponentIntegration(unittest.TestCase):
    """Test cases for component integration and data flow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.component_path = Path(__file__).parent.parent.parent / 'humanauth-render' / 'frontend' / 'src' / 'app' / 'auth-page'
        self.ts_file = self.component_path / 'auth-page.component.ts'
    
    def test_service_dependency_injection(self):
        """Test service dependency injection"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test constructor injection
        constructor_match = re.search(r'constructor\s*\(([^)]+)\)', content, re.DOTALL)
        if constructor_match:
            constructor_params = constructor_match.group(1)
            
            # Test service injections
            expected_services = ['CameraService', 'AuthService', 'NgZone']
            for service in expected_services:
                self.assertIn(service, constructor_params, f"Should inject {service}")
    
    def test_error_handling(self):
        """Test error handling implementation"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test try-catch blocks
        self.assertIn('try {', content, "Should have try-catch error handling")
        self.assertIn('catch', content, "Should have catch blocks")
        
        # Test error state management
        error_patterns = ['this.error =', 'this.fail(', 'setState.*Error']
        has_error_handling = any(re.search(pattern, content) for pattern in error_patterns)
        self.assertTrue(has_error_handling, "Should handle errors properly")
    
    def test_memory_management(self):
        """Test memory management and cleanup"""
        if not self.ts_file.exists():
            self.skipTest("TypeScript file not found")
        
        with open(self.ts_file, 'r') as f:
            content = f.read()
        
        # Test cleanup patterns
        cleanup_patterns = [
            'removeEventListener', 'cancelAnimationFrame', 'disconnect', 'stop'
        ]
        
        # Check ngOnDestroy for cleanup
        ngOnDestroy_match = re.search(r'ngOnDestroy\(\)\s*{([^}]+)}', content, re.DOTALL)
        if ngOnDestroy_match:
            ngOnDestroy_content = ngOnDestroy_match.group(1)
            has_cleanup = any(pattern in ngOnDestroy_content for pattern in cleanup_patterns)
            self.assertTrue(has_cleanup, "ngOnDestroy should perform proper cleanup")

def run_frontend_tests():
    """Run all frontend component tests and return results"""
    print("🧪 Running Frontend Component Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestAuthPageComponent))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthPageTemplate))
    suite.addTests(loader.loadTestsFromTestCase(TestAuthPageStyles))
    suite.addTests(loader.loadTestsFromTestCase(TestComponentIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_frontend_tests()
    sys.exit(0 if success else 1)