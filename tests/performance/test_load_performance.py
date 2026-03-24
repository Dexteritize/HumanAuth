#!/usr/bin/env python3
"""
Performance and load testing for HumanAuth system.
Tests system performance under various load conditions.
"""

import unittest
import requests
import time
import threading
import queue
import statistics
import base64
import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import gc

class TestSystemPerformance(unittest.TestCase):
    """Test system performance under normal conditions"""
    
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
        
        self.dummy_image_data = base64.b64encode(b'dummy_image_data' * 100).decode('utf-8')  # Larger payload
    
    def test_single_session_performance(self):
        """Test performance of a single session processing multiple frames"""
        # Create session
        response = requests.post(f"{self.backend_url}/sessions")
        session_id = response.json()['data']['session_id']
        
        # Measure frame processing times
        frame_count = 100
        processing_times = []
        
        for i in range(frame_count):
            start_time = time.time()
            
            frame_data = {'frame': self.dummy_image_data}
            response = requests.post(
                f"{self.backend_url}/sessions/{session_id}/process",
                json=frame_data
            )
            
            end_time = time.time()
            processing_time = end_time - start_time
            processing_times.append(processing_time)
            
            self.assertEqual(response.status_code, 200)
        
        # Analyze performance metrics
        avg_time = statistics.mean(processing_times)
        median_time = statistics.median(processing_times)
        max_time = max(processing_times)
        min_time = min(processing_times)
        std_dev = statistics.stdev(processing_times)
        
        print(f"\nSingle Session Performance Metrics:")
        print(f"  Frames processed: {frame_count}")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Median time: {median_time:.3f}s")
        print(f"  Min time: {min_time:.3f}s")
        print(f"  Max time: {max_time:.3f}s")
        print(f"  Std deviation: {std_dev:.3f}s")
        
        # Performance assertions
        self.assertLess(avg_time, 3.0, f"Average processing time too slow: {avg_time:.3f}s")
        self.assertLess(max_time, 10.0, f"Maximum processing time too slow: {max_time:.3f}s")
        self.assertLess(std_dev, 2.0, f"Processing time too inconsistent: {std_dev:.3f}s")
    
    def test_session_creation_performance(self):
        """Test session creation performance"""
        session_count = 50
        creation_times = []
        
        for _ in range(session_count):
            start_time = time.time()
            response = requests.post(f"{self.backend_url}/sessions")
            end_time = time.time()
            
            creation_time = end_time - start_time
            creation_times.append(creation_time)
            
            self.assertEqual(response.status_code, 200)
        
        # Analyze metrics
        avg_time = statistics.mean(creation_times)
        max_time = max(creation_times)
        
        print(f"\nSession Creation Performance:")
        print(f"  Sessions created: {session_count}")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Max time: {max_time:.3f}s")
        
        # Performance assertions
        self.assertLess(avg_time, 1.0, f"Session creation too slow: {avg_time:.3f}s")
        self.assertLess(max_time, 5.0, f"Slowest session creation too slow: {max_time:.3f}s")
    
    def test_memory_usage_single_session(self):
        """Test memory usage during single session processing"""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create session and process frames
        response = requests.post(f"{self.backend_url}/sessions")
        session_id = response.json()['data']['session_id']
        
        frame_count = 50
        for _ in range(frame_count):
            frame_data = {'frame': self.dummy_image_data}
            requests.post(f"{self.backend_url}/sessions/{session_id}/process", json=frame_data)
        
        # Force garbage collection
        gc.collect()
        time.sleep(1)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory Usage (Single Session):")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(f"  Frames processed: {frame_count}")
        
        # Memory should not increase excessively
        self.assertLess(memory_increase, 100, f"Memory usage increased too much: {memory_increase:.1f} MB")

class TestLoadTesting(unittest.TestCase):
    """Test system under load conditions"""
    
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
        
        self.dummy_image_data = base64.b64encode(b'dummy_image_data' * 50).decode('utf-8')
    
    def test_concurrent_sessions_load(self):
        """Test system performance with concurrent sessions"""
        concurrent_sessions = 10
        frames_per_session = 20
        results = queue.Queue()
        
        def process_session():
            session_times = []
            session_success = True
            
            try:
                # Create session
                start_time = time.time()
                response = requests.post(f"{self.backend_url}/sessions", timeout=10)
                if response.status_code != 200:
                    results.put({'success': False, 'error': 'Session creation failed'})
                    return
                
                session_id = response.json()['data']['session_id']
                
                # Process frames
                for _ in range(frames_per_session):
                    frame_start = time.time()
                    frame_data = {'frame': self.dummy_image_data}
                    response = requests.post(
                        f"{self.backend_url}/sessions/{session_id}/process",
                        json=frame_data,
                        timeout=15
                    )
                    frame_end = time.time()
                    
                    if response.status_code != 200:
                        session_success = False
                        break
                    
                    session_times.append(frame_end - frame_start)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                results.put({
                    'success': session_success,
                    'total_time': total_time,
                    'frame_times': session_times,
                    'frames_processed': len(session_times)
                })
                
            except Exception as e:
                results.put({'success': False, 'error': str(e)})
        
        # Start concurrent sessions
        print(f"\nStarting {concurrent_sessions} concurrent sessions...")
        start_time = time.time()
        
        threads = []
        for _ in range(concurrent_sessions):
            thread = threading.Thread(target=process_session)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_test_time = end_time - start_time
        
        # Collect and analyze results
        successful_sessions = 0
        all_frame_times = []
        total_frames = 0
        
        while not results.empty():
            result = results.get()
            if result['success']:
                successful_sessions += 1
                all_frame_times.extend(result['frame_times'])
                total_frames += result['frames_processed']
        
        success_rate = successful_sessions / concurrent_sessions
        avg_frame_time = statistics.mean(all_frame_times) if all_frame_times else 0
        
        print(f"\nConcurrent Load Test Results:")
        print(f"  Concurrent sessions: {concurrent_sessions}")
        print(f"  Successful sessions: {successful_sessions}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Total test time: {total_test_time:.2f}s")
        print(f"  Total frames processed: {total_frames}")
        print(f"  Average frame time: {avg_frame_time:.3f}s")
        
        # Performance assertions
        self.assertGreater(success_rate, 0.8, f"Success rate too low: {success_rate:.2%}")
        self.assertLess(avg_frame_time, 5.0, f"Average frame time too slow: {avg_frame_time:.3f}s")
        self.assertLess(total_test_time, 120, f"Total test time too long: {total_test_time:.2f}s")
    
    def test_burst_load(self):
        """Test system response to burst load"""
        burst_size = 50
        burst_duration = 10  # seconds
        
        results = []
        start_time = time.time()
        
        def send_request():
            try:
                request_start = time.time()
                response = requests.post(f"{self.backend_url}/sessions", timeout=5)
                request_end = time.time()
                
                return {
                    'success': response.status_code == 200,
                    'response_time': request_end - request_start,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                }
        
        # Send burst of requests
        with ThreadPoolExecutor(max_workers=burst_size) as executor:
            futures = [executor.submit(send_request) for _ in range(burst_size)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                # Stop if burst duration exceeded
                if time.time() - start_time > burst_duration:
                    break
        
        # Analyze results
        successful_requests = sum(1 for r in results if r['success'])
        success_rate = successful_requests / len(results)
        response_times = [r['response_time'] for r in results if r['success']]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        print(f"\nBurst Load Test Results:")
        print(f"  Burst size: {burst_size}")
        print(f"  Requests sent: {len(results)}")
        print(f"  Successful requests: {successful_requests}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Average response time: {avg_response_time:.3f}s")
        
        # Performance assertions
        self.assertGreater(success_rate, 0.7, f"Burst success rate too low: {success_rate:.2%}")
        self.assertLess(avg_response_time, 3.0, f"Burst response time too slow: {avg_response_time:.3f}s")

class TestStressTesting(unittest.TestCase):
    """Stress testing to find system limits"""
    
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
        
        self.dummy_image_data = base64.b64encode(b'dummy_image_data' * 10).decode('utf-8')
    
    def test_maximum_concurrent_sessions(self):
        """Test maximum number of concurrent sessions the system can handle"""
        max_sessions_to_test = 20
        successful_sessions = 0
        
        def create_session():
            try:
                response = requests.post(f"{self.backend_url}/sessions", timeout=10)
                return response.status_code == 200
            except:
                return False
        
        # Gradually increase concurrent sessions
        for session_count in [5, 10, 15, 20]:
            print(f"\nTesting {session_count} concurrent sessions...")
            
            with ThreadPoolExecutor(max_workers=session_count) as executor:
                futures = [executor.submit(create_session) for _ in range(session_count)]
                successes = sum(1 for future in as_completed(futures) if future.result())
            
            success_rate = successes / session_count
            print(f"  Success rate: {success_rate:.2%} ({successes}/{session_count})")
            
            if success_rate >= 0.8:
                successful_sessions = session_count
            else:
                break
        
        print(f"\nMaximum concurrent sessions: {successful_sessions}")
        self.assertGreaterEqual(successful_sessions, 5, "System should handle at least 5 concurrent sessions")
    
    def test_long_running_stress(self):
        """Test system stability under prolonged stress"""
        duration_minutes = 2  # Reduced for testing
        session_count = 5
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        results = {'successes': 0, 'failures': 0, 'total_requests': 0}
        
        def stress_worker():
            while time.time() < end_time:
                try:
                    # Create session
                    response = requests.post(f"{self.backend_url}/sessions", timeout=5)
                    results['total_requests'] += 1
                    
                    if response.status_code == 200:
                        session_id = response.json()['data']['session_id']
                        
                        # Process a few frames
                        for _ in range(3):
                            frame_data = {'frame': self.dummy_image_data}
                            frame_response = requests.post(
                                f"{self.backend_url}/sessions/{session_id}/process",
                                json=frame_data,
                                timeout=5
                            )
                            results['total_requests'] += 1
                            
                            if frame_response.status_code == 200:
                                results['successes'] += 1
                            else:
                                results['failures'] += 1
                        
                        results['successes'] += 1  # For session creation
                    else:
                        results['failures'] += 1
                        
                except Exception:
                    results['failures'] += 1
                
                time.sleep(0.1)  # Small delay between requests
        
        # Start stress workers
        threads = []
        for _ in range(session_count):
            thread = threading.Thread(target=stress_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Analyze results
        total_requests = results['total_requests']
        success_rate = results['successes'] / total_requests if total_requests > 0 else 0
        
        print(f"\nLong-running Stress Test Results:")
        print(f"  Duration: {duration_minutes} minutes")
        print(f"  Concurrent workers: {session_count}")
        print(f"  Total requests: {total_requests}")
        print(f"  Successful requests: {results['successes']}")
        print(f"  Failed requests: {results['failures']}")
        print(f"  Success rate: {success_rate:.2%}")
        
        # System should maintain reasonable success rate under stress
        self.assertGreater(success_rate, 0.6, f"Stress test success rate too low: {success_rate:.2%}")
        self.assertGreater(total_requests, 50, "Should process reasonable number of requests")

def run_performance_tests():
    """Run all performance tests and return results"""
    print("🧪 Running Performance and Load Tests...")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSystemPerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestLoadTesting))
    suite.addTests(loader.loadTestsFromTestCase(TestStressTesting))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)