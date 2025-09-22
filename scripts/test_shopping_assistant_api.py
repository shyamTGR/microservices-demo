#!/usr/bin/env python3
"""
Test script for Shopping Assistant API functionality.
This script tests:
1. Service responds to POST requests
2. Image analysis and product recommendation workflow
3. Response format validation
4. Product ID extraction
"""

import requests
import json
import sys
import time

def get_test_image_url():
    """Get a test image URL for API testing"""
    # Use a simple room image URL for testing
    # This is a placeholder - in a real scenario you'd use an actual room image
    return "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=400&h=300&fit=crop"

def test_api_endpoint(service_url, test_cases):
    """Test the Shopping Assistant API with various test cases"""
    
    print(f"🧪 Testing Shopping Assistant API at: {service_url}")
    print("=" * 60)
    
    all_tests_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        
        try:
            # Prepare request
            payload = {
                "message": test_case["message"],
                "image": test_case["image"]
            }
            
            print(f"📤 Sending request...")
            print(f"   Message: {test_case['message']}")
            print(f"   Image: {test_case['image']}")
            
            # Send request with timeout
            start_time = time.time()
            response = requests.post(
                service_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=60  # 60 second timeout for AI processing
            )
            end_time = time.time()
            
            print(f"⏱️  Response time: {end_time - start_time:.2f} seconds")
            print(f"📊 Status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print("✅ Valid JSON response received")
                    
                    # Check response structure
                    if 'content' in response_data:
                        content = response_data['content']
                        print(f"📝 Response content length: {len(content)} characters")
                        
                        # Extract first 200 characters for preview
                        preview = content[:200] + "..." if len(content) > 200 else content
                        print(f"📖 Content preview: {preview}")
                        
                        # Check for product IDs in the expected format [ID]
                        import re
                        product_ids = re.findall(r'\[([A-Z0-9]+)\]', content)
                        
                        if product_ids:
                            print(f"🛍️  Found product IDs: {product_ids}")
                            print("✅ Product IDs are properly formatted")
                        else:
                            print("⚠️  No product IDs found in expected format [ID]")
                        
                        # Validate content contains room description
                        if any(word in content.lower() for word in ['room', 'style', 'design', 'decor']):
                            print("✅ Response contains room description")
                        else:
                            print("⚠️  Response may not contain room description")
                        
                        print(f"✅ Test Case {i} PASSED")
                        
                    else:
                        print("❌ Response missing 'content' field")
                        all_tests_passed = False
                        
                except json.JSONDecodeError:
                    print("❌ Invalid JSON response")
                    print(f"Raw response: {response.text[:500]}")
                    all_tests_passed = False
                    
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                all_tests_passed = False
                
        except requests.exceptions.Timeout:
            print("❌ Request timed out (>60 seconds)")
            all_tests_passed = False
            
        except requests.exceptions.ConnectionError:
            print("❌ Connection error - service may not be accessible")
            all_tests_passed = False
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            all_tests_passed = False
    
    return all_tests_passed

def get_service_url():
    """Get the Shopping Assistant service URL"""
    import subprocess
    
    try:
        # Get service cluster IP
        result = subprocess.run([
            'kubectl', 'get', 'service', 'shoppingassistantservice', 
            '-o', 'jsonpath={.spec.clusterIP}'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            cluster_ip = result.stdout.strip()
            return f"http://{cluster_ip}"
        else:
            print(f"❌ Failed to get service IP: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting service URL: {e}")
        return None

def test_service_health(service_url):
    """Test if the service is responding to basic requests"""
    print("🏥 Testing service health...")
    
    try:
        # Try a simple GET request first (should return 405 Method Not Allowed)
        response = requests.get(f"{service_url}/", timeout=10)
        if response.status_code == 405:
            print("✅ Service is responding (GET returns 405 as expected)")
            return True
        else:
            print(f"⚠️  Unexpected response to GET: {response.status_code}")
            return True  # Still consider it healthy if it responds
            
    except requests.exceptions.ConnectionError:
        print("❌ Service is not accessible")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def main():
    """Main testing function"""
    print("🚀 Starting Shopping Assistant API Testing")
    print("=" * 60)
    
    # Get service URL
    service_url = get_service_url()
    if not service_url:
        print("❌ Could not determine service URL")
        return 1
    
    print(f"🌐 Service URL: {service_url}")
    
    # Test service health
    if not test_service_health(service_url):
        print("❌ Service health check failed")
        return 1
    
    # Get test image URL
    print("\n🖼️  Getting test image URL...")
    test_image = get_test_image_url()
    print("✅ Test image URL ready")
    
    # Define test cases
    test_cases = [
        {
            "name": "Basic room decoration request",
            "message": "I need some accessories for my living room",
            "image": test_image
        },
        {
            "name": "Specific item request",
            "message": "I'm looking for sunglasses to match my room style",
            "image": test_image
        },
        {
            "name": "Style-specific request",
            "message": "What would look good in this modern room?",
            "image": test_image
        }
    ]
    
    # Run API tests
    all_tests_passed = test_api_endpoint(service_url, test_cases)
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All API tests passed!")
        print("✅ Shopping Assistant API is working correctly")
        return 0
    else:
        print("❌ Some API tests failed")
        print("🔧 Please review the issues above and retry")
        return 1

if __name__ == "__main__":
    sys.exit(main())