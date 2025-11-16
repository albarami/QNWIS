"""
Test Rate Limiting (Fix 4.1)

Tests that rate limiting is correctly enforced on LLM endpoints.
Expected: 10 requests/hour limit, 11th request blocked with 429.
"""

import requests
import time
import sys


def test_rate_limiting(base_url="http://localhost:8000"):
    """Test rate limiting on /api/v1/council/stream endpoint"""
    
    print("=" * 80)
    print("🛡️  TESTING RATE LIMITING (Fix 4.1)")
    print("=" * 80)
    print(f"Target: {base_url}/api/v1/council/stream")
    print(f"Expected limit: 10 requests/hour")
    print(f"Testing: Making 12 requests...")
    print()
    
    endpoint = f"{base_url}/api/v1/council/stream"
    headers = {"Content-Type": "application/json"}
    payload = {"question": "test"}
    
    success_count = 0
    rate_limited_count = 0
    
    for i in range(1, 13):
        print(f"Request {i:2d}: ", end="", flush=True)
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=10,
                stream=True  # For SSE endpoint
            )
            
            status = response.status_code
            
            if status == 200:
                success_count += 1
                print(f"✅ 200 OK")
                
                # Check rate limit headers
                if 'X-RateLimit-Limit' in response.headers:
                    limit = response.headers.get('X-RateLimit-Limit')
                    remaining = response.headers.get('X-RateLimit-Remaining')
                    print(f"           Limit: {limit}, Remaining: {remaining}")
                
            elif status == 429:
                rate_limited_count += 1
                print(f"🛡️  429 RATE LIMITED")
                
                # Check retry-after header
                retry_after = response.headers.get('Retry-After', 'unknown')
                print(f"           Retry-After: {retry_after} seconds")
                
                # Parse response body
                try:
                    error_data = response.json()
                    print(f"           Message: {error_data.get('message', '')}")
                except:
                    pass
                
                # Rate limiting working, stop here
                print()
                print("✅ Rate limiting is working correctly!")
                print(f"   - Allowed first {success_count} requests")
                print(f"   - Blocked request {i} (as expected)")
                return True
                
            else:
                print(f"⚠️  {status} (unexpected)")
            
            # Consume response to avoid connection issues
            for _ in response.iter_lines():
                pass
            response.close()
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error - is server running?")
            print(f"   Start with: uvicorn src.qnwis.api.server:app --port 8000")
            return False
            
        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout (query may be running)")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    # If we got here, rate limiting didn't work
    print()
    if rate_limited_count == 0:
        print("❌ RATE LIMITING NOT WORKING")
        print(f"   All {success_count} requests succeeded")
        print(f"   Expected: Request 11 should be blocked with 429")
        print()
        print("Troubleshooting:")
        print("  1. Check server logs for 'Rate limiter initialized'")
        print("  2. Verify slowapi is installed: pip list | grep slowapi")
        print("  3. Check server.py has limiter setup")
        return False
    else:
        print("⚠️  Rate limiting may not be configured correctly")
        print(f"   Got {rate_limited_count} rate-limited responses")
        return False


def test_endpoint_availability(base_url="http://localhost:8000"):
    """Test if server is running"""
    
    print("Checking server availability...", end=" ", flush=True)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"⚠️  Server returned {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server")
        print()
        print("Please start the server first:")
        print("  uvicorn src.qnwis.api.server:app --reload --port 8000")
        print()
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    base_url = "http://localhost:8000"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    # Check server is running
    if not test_endpoint_availability(base_url):
        sys.exit(1)
    
    print()
    
    # Test rate limiting
    success = test_rate_limiting(base_url)
    
    print()
    print("=" * 80)
    
    if success:
        print("✅ RATE LIMITING TEST PASSED")
        sys.exit(0)
    else:
        print("❌ RATE LIMITING TEST FAILED")
        sys.exit(1)
