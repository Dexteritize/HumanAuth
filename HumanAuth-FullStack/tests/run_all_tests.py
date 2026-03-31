#!/usr/bin/env python3
"""
Master Test Runner for HumanAuth Comprehensive Test Suite

This script orchestrates all test modules and provides a unified interface
for running the complete test suite or specific test categories.

Usage:
    python tests/run_all_tests.py                    # Run all tests
    python tests/run_all_tests.py --backend          # Run only backend tests
    python tests/run_all_tests.py --frontend         # Run only frontend tests
    python tests/run_all_tests.py --e2e              # Run only e2e tests
    python tests/run_all_tests.py --performance      # Run only performance tests
    python tests/run_all_tests.py --security         # Run only security tests
    python tests/run_all_tests.py --quick            # Run quick test subset
    python tests/run_all_tests.py --report           # Generate detailed report
    python tests/run_all_tests.py --verbose          # Verbose output
"""

import sys
import os
import argparse
import time
import json
from pathlib import Path
from datetime import datetime
import subprocess
import importlib.util

# Add the tests directory to Python path
tests_dir = Path(__file__).parent
sys.path.insert(0, str(tests_dir))

class TestRunner:
    """Master test runner for HumanAuth test suite"""
    
    def __init__(self):
        self.start_time = None
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        
        # Test module configurations
        self.test_modules = {
            'backend': {
                'name': 'Backend API Tests',
                'modules': [
                    'backend.test_human_auth',
                    'backend.test_app',
                    'backend.test_auth_types',
                    'backend.test_visualization'
                ],
                'description': 'Tests for backend API endpoints, authentication logic, and data structures'
            },
            'frontend': {
                'name': 'Frontend Component Tests',
                'modules': [
                    'frontend.test_auth_page_component'
                ],
                'description': 'Tests for Angular components, services, and UI functionality'
            },
            'e2e': {
                'name': 'End-to-End Integration Tests',
                'modules': [
                    'e2e.test_full_authentication_flow'
                ],
                'description': 'Complete system integration tests from frontend to backend'
            },
            'performance': {
                'name': 'Performance and Load Tests',
                'modules': [
                    'performance.test_load_performance'
                ],
                'description': 'Performance testing under various load conditions'
            },
            'security': {
                'name': 'Security Vulnerability Tests',
                'modules': [
                    'security.test_security_vulnerabilities'
                ],
                'description': 'Security testing for common vulnerabilities and attack vectors'
            },
            'auth_display': {
                'name': 'Authentication Display Tests',
                'modules': [
                    'auth_display.test_auth_display_system',
                    'auth_display.test_enhanced_display'
                ],
                'description': 'Tests for authentication display functionality and UI components'
            },
            'integration': {
                'name': 'Integration Tests',
                'modules': [
                    'integration.test_complete_solution'
                ],
                'description': 'Integration tests for complete solution workflows'
            },
            'verification': {
                'name': 'Verification Scripts',
                'modules': [
                    'verification.verify_auth_fix',
                    'verification.verify_auth_display'
                ],
                'description': 'Verification scripts for manual and automated validation'
            }
        }
    
    def print_banner(self):
        """Print test suite banner"""
        print("=" * 80)
        print("🧪 HUMANAUTH COMPREHENSIVE TEST SUITE")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    def print_summary(self):
        """Print test execution summary"""
        end_time = time.time()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 TEST EXECUTION SUMMARY")
        print("=" * 80)
        
        # Overall results
        print(f"⏱️  Total Duration: {duration:.2f} seconds")
        print(f"📈 Total Tests: {self.total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"⏭️  Skipped: {self.skipped_tests}")
        
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")
        
        print("\n📋 Results by Category:")
        for category, result in self.results.items():
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            print(f"  {category:20} {status:10} ({result['duration']:.2f}s)")
        
        # Overall status
        overall_success = all(result['success'] for result in self.results.values())
        print(f"\n🎯 Overall Status: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success
    
    def run_test_module(self, module_path, category_name):
        """Run a specific test module"""
        print(f"\n🔍 Running {category_name}...")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            # Import and run the test module
            spec = importlib.util.spec_from_file_location(
                module_path.replace('.', '_'), 
                tests_dir / f"{module_path.replace('.', '/')}.py"
            )
            
            if spec is None or spec.loader is None:
                print(f"❌ Could not load module: {module_path}")
                return False
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for the run function
            run_function_name = f"run_{module_path.split('.')[-1].replace('test_', '')}_tests"
            if hasattr(module, run_function_name):
                success = getattr(module, run_function_name)()
            else:
                print(f"⚠️  No run function found for {module_path}")
                success = False
            
            end_time = time.time()
            duration = end_time - start_time
            
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"\n{status} - {category_name} ({duration:.2f}s)")
            
            return success
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"❌ ERROR in {category_name}: {str(e)}")
            print(f"❌ FAILED - {category_name} ({duration:.2f}s)")
            return False
    
    def run_test_category(self, category):
        """Run all tests in a specific category"""
        if category not in self.test_modules:
            print(f"❌ Unknown test category: {category}")
            return False
        
        config = self.test_modules[category]
        print(f"\n🚀 Starting {config['name']}")
        print(f"📝 {config['description']}")
        
        start_time = time.time()
        category_success = True
        
        for module_path in config['modules']:
            module_success = self.run_test_module(module_path, f"{config['name']} - {module_path}")
            if not module_success:
                category_success = False
        
        end_time = time.time()
        duration = end_time - start_time
        
        self.results[category] = {
            'success': category_success,
            'duration': duration
        }
        
        return category_success
    
    def run_quick_tests(self):
        """Run a quick subset of tests for rapid feedback"""
        print("🚀 Running Quick Test Suite...")
        print("📝 Essential tests for rapid feedback")
        
        quick_categories = ['backend', 'frontend']
        overall_success = True
        
        for category in quick_categories:
            if category in self.test_modules:
                success = self.run_test_category(category)
                if not success:
                    overall_success = False
        
        return overall_success
    
    def check_prerequisites(self):
        """Check if prerequisites are met for running tests"""
        print("🔍 Checking Prerequisites...")
        
        # Check if backend is running (for integration tests)
        try:
            import requests
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ Backend service is running")
                backend_running = True
            else:
                print("⚠️  Backend service not responding properly")
                backend_running = False
        except Exception:
            print("⚠️  Backend service not accessible")
            backend_running = False
        
        # Check Python dependencies
        required_packages = ['requests', 'numpy', 'cv2', 'unittest']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package} available")
            except ImportError:
                print(f"❌ {package} not available")
                missing_packages.append(package)
        
        if missing_packages:
            print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
            print("Install with: pip install " + " ".join(missing_packages))
        
        return len(missing_packages) == 0, backend_running
    
    def generate_report(self):
        """Generate detailed test report"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'duration': time.time() - self.start_time if self.start_time else 0,
            'summary': {
                'total_tests': self.total_tests,
                'passed': self.passed_tests,
                'failed': self.failed_tests,
                'skipped': self.skipped_tests,
                'success_rate': (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            'results': self.results
        }
        
        # Save report to file
        report_file = tests_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        return report_file
    
    def run_all_tests(self):
        """Run all test categories"""
        print("🚀 Running Complete Test Suite...")
        
        overall_success = True
        
        # Run tests in logical order
        test_order = ['backend', 'frontend', 'auth_display', 'integration', 'e2e', 'performance', 'security', 'verification']
        
        for category in test_order:
            if category in self.test_modules:
                success = self.run_test_category(category)
                if not success:
                    overall_success = False
        
        return overall_success

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="HumanAuth Comprehensive Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_all_tests.py                    # Run all tests
  python tests/run_all_tests.py --backend          # Run only backend tests
  python tests/run_all_tests.py --quick            # Run quick test subset
  python tests/run_all_tests.py --report           # Generate detailed report
        """
    )
    
    # Test category options
    parser.add_argument('--backend', action='store_true', help='Run backend API tests')
    parser.add_argument('--frontend', action='store_true', help='Run frontend component tests')
    parser.add_argument('--e2e', action='store_true', help='Run end-to-end integration tests')
    parser.add_argument('--performance', action='store_true', help='Run performance and load tests')
    parser.add_argument('--security', action='store_true', help='Run security vulnerability tests')
    parser.add_argument('--auth-display', action='store_true', help='Run authentication display tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--verification', action='store_true', help='Run verification scripts')
    
    # Execution options
    parser.add_argument('--quick', action='store_true', help='Run quick test subset for rapid feedback')
    parser.add_argument('--report', action='store_true', help='Generate detailed test report')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--no-prereq-check', action='store_true', help='Skip prerequisite checks')
    
    args = parser.parse_args()
    
    # Create test runner
    runner = TestRunner()
    runner.start_time = time.time()
    
    # Print banner
    runner.print_banner()
    
    # Check prerequisites unless skipped
    if not args.no_prereq_check:
        deps_ok, backend_running = runner.check_prerequisites()
        if not deps_ok:
            print("\n❌ Prerequisites not met. Please install missing dependencies.")
            return 1
        
        if not backend_running:
            print("\n⚠️  Backend not running. Some tests may be skipped.")
            print("Start backend with: cd HumanAuth-FullStack && ./start.sh")
    
    # Determine which tests to run
    specific_categories = []
    if args.backend:
        specific_categories.append('backend')
    if args.frontend:
        specific_categories.append('frontend')
    if args.e2e:
        specific_categories.append('e2e')
    if args.performance:
        specific_categories.append('performance')
    if args.security:
        specific_categories.append('security')
    if args.auth_display:
        specific_categories.append('auth_display')
    if args.integration:
        specific_categories.append('integration')
    if args.verification:
        specific_categories.append('verification')
    
    # Run tests
    try:
        if args.quick:
            success = runner.run_quick_tests()
        elif specific_categories:
            success = True
            for category in specific_categories:
                category_success = runner.run_test_category(category)
                if not category_success:
                    success = False
        else:
            success = runner.run_all_tests()
        
        # Print summary
        overall_success = runner.print_summary()
        
        # Generate report if requested
        if args.report:
            runner.generate_report()
        
        # Return appropriate exit code
        return 0 if overall_success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test execution interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error during test execution: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())