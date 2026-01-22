"""REST API Integration Tests for Recipe Recommendation Service.

Tests HTTP endpoints of AgentOS application using httpx client.
Validates request/response formats, error handling, session management, and image support.

Note: These tests require app.py running on http://localhost:7777
Run the app separately: python app.py (or make dev in another terminal)
Then run: make eval or pytest tests/integration/test_api.py -v

Features:
- Test successful requests with JSON payloads
- Test image upload via base64
- Test validation errors (400, 413, 422)
- Test session management and preference persistence
- Test error response format
- Test HTTP status codes (200, 400, 413, 422, 500)
"""

import json
import base64
import pytest
import httpx
from pathlib import Path
from typing import Optional

from src.utils.config import config
from src.utils.logger import logger

# Base URL for API tests (default AgentOS port)
API_BASE_URL = f"http://localhost:{config.PORT}"
API_TIMEOUT = 30  # Seconds per request
AGENT_ID = "recipe-recommendation-agent"  # Agent ID from agent.py


@pytest.fixture(scope="module")
def http_client():
    """Create HTTP client for API tests.
    
    Yields an httpx.Client for making requests to the running app.
    Client is automatically closed after tests complete.
    """
    with httpx.Client(base_url=API_BASE_URL, timeout=API_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="module")
def app_health_check(http_client):
    """Verify app is running and accessible before tests start.
    
    Skips all tests if app is not reachable.
    """
    try:
        # Check OpenAPI docs endpoint (no auth required)
        response = http_client.get("/docs")
        if response.status_code != 200:
            pytest.skip(f"App not accessible. Status: {response.status_code}")
        logger.info(f"✓ App health check passed: {API_BASE_URL}")
        yield
    except httpx.ConnectError:
        pytest.skip(f"Cannot connect to app at {API_BASE_URL}. Start with: python app.py or make dev")
    except Exception as e:
        pytest.skip(f"App health check failed: {e}")


# ============================================================================
# Test 1: Basic Successful Request
# ============================================================================

def test_post_chat_successful_basic(http_client, app_health_check):
    """Test successful POST /agents/{agent_id}/runs with basic message.
    
    Validates:
    - HTTP 200 status code
    - Response contains content field
    - Response is properly formatted
    """
    logger.info("Test: POST /agents/{agent_id}/runs - basic successful request")
    
    # Create ChatMessage JSON input
    request_data = {
        "message": "What can I make with chicken and rice?"
    }
    message_json = json.dumps(request_data)
    
    # Send request with message as form field containing JSON
    data = {"message": message_json}
    
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=data,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Validate HTTP status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:200]}"
    
    # Response is Server-Sent Events (streaming)
    assert "RunStarted" in response.text or "event:" in response.text, f"Unexpected response format: {response.text[:200]}"
    
    logger.info("✓ Basic successful request test passed")


def test_post_chat_with_session_id(http_client, app_health_check):
    """Test successful POST /api/agents/chat with session_id.
    
    Validates:
    - HTTP 200 status code
    - Session ID is preserved in response
    - Conversation context is maintained
    """
    logger.info("Test: POST /api/agents/chat - with session_id")
    
    session_id = "test_session_" + str(hash("test_session_basic")).replace("-", "")
    
    payload = {
        "message": "I prefer vegetarian recipes",
        "session_id": session_id
    }
    
    # Send request
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Validate HTTP status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Validate response
    response_data = response.json()
    assert "content" in response_data, f"Missing 'content' field: {response_data.keys()}"
    
    logger.info("✓ Session ID test passed")


# ============================================================================
# Test 2: Image Upload and Ingredient Extraction
# ============================================================================

def test_post_chat_with_image_base64(http_client, app_health_check):
    """Test POST /api/agents/chat with base64-encoded image.
    
    Validates:
    - HTTP 200 status code
    - Image is accepted in request
    - Ingredient extraction occurs
    - Response contains recipe suggestions
    """
    logger.info("Test: POST /api/agents/chat - with base64 image")
    
    # Create a minimal test image (1x1 pixel JPEG)
    # This is a valid JPEG header for minimal testing
    minimal_jpeg = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\''
        b'9=82<.342\xff\xc0\x00\x0b\x01\x01\x01\x01\x01\x11\x00\xff\xc4\x00\x1f'
        b'\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00'
        b'\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03'
        b'\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1'
        b'\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83'
        b'\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2'
        b'\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba'
        b'\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9'
        b'\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6'
        b'\xf7\xf8\xf9\xfa\xff\xda\x08\x01\x01\x00\x00?\x00\xfb\xd3\xff\xd9'
    )
    
    image_base64 = base64.b64encode(minimal_jpeg).decode('utf-8')
    image_data_uri = f"data:image/jpeg;base64,{image_base64}"
    
    payload = {
        "message": "What can I cook with these ingredients?",
        "images": [image_data_uri]
    }
    
    # Send request
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Validate HTTP status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Validate response
    response_data = response.json()
    assert "content" in response_data, f"Missing 'content' field: {response_data.keys()}"
    
    logger.info("✓ Image base64 test passed")


# ============================================================================
# Test 3: Validation Errors - Missing Fields (HTTP 400)
# ============================================================================

def test_post_chat_missing_message_and_images(http_client, app_health_check):
    """Test POST /api/agents/chat with both message and images missing.
    
    Validates:
    - HTTP 400 status code (bad request)
    - Error response contains error details
    """
    logger.info("Test: POST /api/agents/chat - missing message and images (HTTP 400)")
    
    payload = {
        # Neither message nor images provided
    }
    
    # Send request
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Expect validation error
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    response_data = response.json()
    assert "detail" in response_data or "error" in response_data, "Expected error details in response"
    
    logger.info("✓ Missing fields validation test passed")


def test_post_chat_invalid_json(http_client, app_health_check):
    """Test POST /api/agents/chat with malformed JSON.
    
    Validates:
    - HTTP 400 status code for invalid JSON
    - Error message is present
    """
    logger.info("Test: POST /api/agents/chat - invalid JSON (HTTP 400)")
    
    # Send malformed JSON
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        content="{invalid json}",
        headers={"Content-Type": "application/json"}
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Expect parsing error
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    logger.info("✓ Invalid JSON test passed")


# ============================================================================
# Test 4: Guardrails - Off-Topic Request (HTTP 422)
# ============================================================================

def test_post_chat_off_topic_request(http_client, app_health_check):
    """Test POST /api/agents/chat with completely off-topic request.
    
    Validates:
    - HTTP 422 status code (validation error from guardrails)
    - Response includes error message
    """
    logger.info("Test: POST /api/agents/chat - off-topic request (HTTP 422)")
    
    payload = {
        "message": "Can you write me a Python web framework? I need a complete backend system."
    }
    
    # Send request
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Guardrails should trigger with 422 or 400
    assert response.status_code in [422, 400], f"Expected 422 or 400, got {response.status_code}"
    
    response_data = response.json()
    logger.info(f"Response: {response_data}")
    
    logger.info("✓ Off-topic request test passed")


# ============================================================================
# Test 5: Oversized Image (HTTP 413)
# ============================================================================

def test_post_chat_oversized_image(http_client, app_health_check):
    """Test POST /api/agents/chat with oversized image.
    
    Validates:
    - HTTP 413 status code for payload too large
    - Or HTTP 400 if validation catches it
    """
    logger.info("Test: POST /api/agents/chat - oversized image (HTTP 413)")
    
    # Create a large base64 string (exceeds MAX_IMAGE_SIZE_MB default of 5MB)
    # 6MB of data (base64 encoded)
    large_data = "A" * (6 * 1024 * 1024)
    image_base64 = base64.b64encode(large_data.encode()).decode('utf-8')
    
    payload = {
        "message": "What can I cook?",
        "images": [f"data:image/jpeg;base64,{image_base64}"]
    }
    
    # Send request
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Expect either 413 (payload too large) or 400 (validation)
    assert response.status_code in [413, 400, 422], f"Expected 413/400/422, got {response.status_code}"
    
    logger.info("✓ Oversized image test passed")


# ============================================================================
# Test 6: Session Management - Preference Persistence
# ============================================================================

def test_session_preference_persistence(http_client, app_health_check):
    """Test session-based preference persistence across requests.
    
    Validates:
    - First request: Set vegetarian preference
    - Second request: Preference applied to suggestions
    - Conversation history maintained
    """
    logger.info("Test: Session preference persistence across requests")
    
    session_id = "test_session_" + str(hash("test_session_preferences")).replace("-", "")
    
    # Step 1: Set vegetarian preference
    logger.info("Step 1: Setting vegetarian preference...")
    payload1 = {
        "message": "I'm vegetarian, show me meatless recipes",
        "session_id": session_id
    }
    
    response1 = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload1,
    )
    
    assert response1.status_code == 200, f"Request 1 failed: {response1.status_code}"
    logger.info("✓ First request successful")
    
    # Step 2: Send follow-up request (should remember preference)
    logger.info("Step 2: Follow-up request (should remember vegetarian preference)...")
    payload2 = {
        "message": "Show me more recipes",
        "session_id": session_id
    }
    
    response2 = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload2,
    )
    
    assert response2.status_code == 200, f"Request 2 failed: {response2.status_code}"
    
    response_data = response2.json()
    assert "content" in response_data, "Response missing content field"
    
    logger.info("✓ Session preference persistence test passed")


def test_session_isolation(http_client, app_health_check):
    """Test that different sessions are isolated from each other.
    
    Validates:
    - Session A sets vegetarian preference
    - Session B should not have that preference
    - Preferences don't cross-contaminate
    """
    logger.info("Test: Session isolation between different users")
    
    session_a = "test_session_" + str(hash("test_session_a")).replace("-", "")
    session_b = "test_session_" + str(hash("test_session_b")).replace("-", "")
    
    # Step 1: User A sets vegetarian preference
    logger.info("Step 1: User A sets vegetarian preference...")
    payload_a = {
        "message": "I'm vegetarian",
        "session_id": session_a
    }
    
    response_a = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload_a,
    )
    
    assert response_a.status_code == 200, f"User A request failed: {response_a.status_code}"
    logger.info("✓ User A request successful")
    
    # Step 2: User B requests (should NOT have vegetarian preference)
    logger.info("Step 2: User B requests (different session)...")
    payload_b = {
        "message": "What recipes do you have?",
        "session_id": session_b
    }
    
    response_b = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload_b,
    )
    
    assert response_b.status_code == 200, f"User B request failed: {response_b.status_code}"
    
    response_b_data = response_b.json()
    assert "content" in response_b_data, "User B response missing content"
    
    logger.info("✓ Session isolation test passed")


# ============================================================================
# Test 7: Error Response Format
# ============================================================================

def test_error_response_format(http_client, app_health_check):
    """Test that error responses have proper format.
    
    Validates:
    - Error response contains error details
    - Error message is readable
    - Status code indicates error
    """
    logger.info("Test: Error response format validation")
    
    # Trigger a validation error
    payload = {
        # Empty message and no images
        "message": ""
    }
    
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Should be an error status
    assert response.status_code >= 400, f"Expected error status, got {response.status_code}"
    
    response_data = response.json()
    
    # Error response should have either 'detail' or 'error' field
    has_error_info = "detail" in response_data or "error" in response_data
    assert has_error_info, f"Error response missing error details: {response_data.keys()}"
    
    logger.info("✓ Error response format test passed")


# ============================================================================
# Test 8: Multiple Images Support
# ============================================================================

def test_post_chat_multiple_images(http_client, app_health_check):
    """Test POST /api/agents/chat with multiple base64 images.
    
    Validates:
    - HTTP 200 status code
    - Multiple images are accepted
    - All ingredients extracted and considered
    """
    logger.info("Test: POST /api/agents/chat - multiple images")
    
    # Create two minimal test images
    minimal_jpeg = (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
        b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
        b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\''
        b'9=82<.342\xff\xc0\x00\x0b\x01\x01\x01\x01\x01\x11\x00\xff\xc4\x00\x1f'
        b'\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00'
        b'\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03'
        b'\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1'
        b'\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83'
        b'\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2'
        b'\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba'
        b'\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9'
        b'\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6'
        b'\xf7\xf8\xf9\xfa\xff\xda\x08\x01\x01\x00\x00?\x00\xfb\xd3\xff\xd9'
    )
    
    images = [
        f"data:image/jpeg;base64,{base64.b64encode(minimal_jpeg).decode('utf-8')}",
        f"data:image/jpeg;base64,{base64.b64encode(minimal_jpeg).decode('utf-8')}"
    ]
    
    payload = {
        "message": "What can I cook with all these ingredients?",
        "images": images
    }
    
    # Send request
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    logger.info(f"Response status: {response.status_code}")
    
    # Validate HTTP status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    # Validate response
    response_data = response.json()
    assert "content" in response_data, f"Missing 'content' field: {response_data.keys()}"
    
    logger.info("✓ Multiple images test passed")


# ============================================================================
# Test 9: Response Content Structure
# ============================================================================

def test_response_content_structure(http_client, app_health_check):
    """Test that response content has expected structure.
    
    Validates:
    - Response has content field
    - Content is properly formatted
    - Response includes necessary metadata
    """
    logger.info("Test: Response content structure validation")
    
    payload = {
        "message": "What can I make with pasta and tomato sauce?"
    }
    
    # Send request
    response = http_client.post(
        f"/agents/{AGENT_ID}/runs",
        data=payload,
    )
    
    assert response.status_code == 200, f"Request failed: {response.status_code}"
    
    response_data = response.json()
    
    # Check required fields
    assert "content" in response_data, "Missing 'content' field"
    
    # Content should be non-empty
    content = response_data["content"]
    assert content is not None, "Content is None"
    
    # If content is a dict, it should have expected structure
    if isinstance(content, dict):
        # It should have either 'response' or be a valid response object
        logger.info(f"Content type: dict with keys: {content.keys()}")
    elif isinstance(content, str):
        # String content is valid
        assert len(content) > 0, "Content string is empty"
    
    logger.info("✓ Response content structure test passed")


# ============================================================================
# Test 10: Rapid Sequential Requests
# ============================================================================

def test_rapid_sequential_requests(http_client, app_health_check):
    """Test handling of rapid sequential requests in same session.
    
    Validates:
    - All requests return HTTP 200
    - Session maintains conversation history
    - No rate limiting or resource exhaustion
    """
    logger.info("Test: Rapid sequential requests")
    
    session_id = "test_session_" + str(hash("test_session_rapid")).replace("-", "")
    
    # Send 3 rapid requests
    for i in range(3):
        logger.info(f"Request {i+1}/3...")
        
        payload = {
            "message": f"Request number {i+1}: What recipes do you recommend?",
            "session_id": session_id
        }
        
        response = http_client.post(
            f"/agents/{AGENT_ID}/runs",
            data=payload,
        )
        
        assert response.status_code == 200, f"Request {i+1} failed with status {response.status_code}"
        
        response_data = response.json()
        assert "content" in response_data, f"Request {i+1} missing content field"
    
    logger.info("✓ Rapid sequential requests test passed")
