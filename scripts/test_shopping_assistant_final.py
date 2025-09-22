#!/usr/bin/env python3
"""
Final test script for Shopping Assistant frontend integration
This script tests the complete end-to-end workflow after database initialization.
"""

import requests
import json
import base64
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
SHOPPING_ASSISTANT_URL = "http://shoppingassistantservice:80/"

# Create a simple test image (1x1 pixel)
def create_test_image():
    """Create a minimal test image as base64."""
    # This is a 1x1 transparent PNG
    return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

def test_shopping_assistant_api():
    """Test the Shopping Assistant API endpoint."""
    logger.info("Testing Shopping Assistant API...")
    
    test_cases = [
        {
            "name": "Accessories Request",
            "message": "I need stylish accessories for my outfit",
            "expected_keywords": ["accessories", "sunglasses", "watch"]
        },
        {
            "name": "Home Decor Request", 
            "message": "I want to decorate my living room",
            "expected_keywords": ["home", "decor", "candle", "typewriter"]
        },
        {
            "name": "Fashion Request",
            "message": "Show me clothing items",
            "expected_keywords": ["clothing", "tank", "top"]
        }
    ]
    
    test_image = create_test_image()
    
    for test_case in test_cases:
        logger.info(f"Running test: {test_case['name']}")
        
        try:
            payload = {
                "message": test_case["message"],
                "image": test_image
            }
            
            response = requests.post(
                SHOPPING_ASSISTANT_URL,
                json=payload,
                timeout=60,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("content", "").lower()
                
                logger.info(f"✅ {test_case['name']} - Status: {response.status_code}")
                logger.info(f"Response preview: {content[:200]}...")
                
                # Check for expected keywords
                found_keywords = [kw for kw in test_case["expected_keywords"] if kw in content]
                if found_keywords:
                    logger.info(f"✅ Found relevant keywords: {found_keywords}")
                else:
                    logger.warning(f"⚠️ No expected keywords found in response")
                
                # Check for product IDs in response
                if "[" in content and "]" in content:
                    logger.info("✅ Response contains product ID format")
                else:
                    logger.warning("⚠️ No product IDs found in response format")
                    
            else:
                logger.error(f"❌ {test_case['name']} - Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error(f"❌ {test_case['name']} - Request timed out")
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ {test_case['name']} - Request failed: {e}")
        except Exception as e:
            logger.error(f"❌ {test_case['name']} - Unexpected error: {e}")
        
        # Wait between tests
        time.sleep(2)

def test_service_health():
    """Test basic service connectivity."""
    logger.info("Testing service connectivity...")
    
    try:
        # Test with minimal payload
        response = requests.post(
            SHOPPING_ASSISTANT_URL,
            json={"message": "test", "image": create_test_image()},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("✅ Service is responding to requests")
            return True
        else:
            logger.error(f"❌ Service returned status: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Service connectivity test failed: {e}")
        return False

def main():
    """Run all frontend integration tests."""
    logger.info("🚀 Starting Shopping Assistant Frontend Integration Tests")
    
    # Test 1: Basic connectivity
    if not test_service_health():
        logger.error("❌ Basic connectivity test failed. Stopping tests.")
        return False
    
    # Test 2: API functionality
    test_shopping_assistant_api()
    
    logger.info("🎉 Frontend integration tests completed!")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)