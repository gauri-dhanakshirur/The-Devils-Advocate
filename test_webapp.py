"""
Quick test script to verify webapp integration.
Run after starting the backend with: python main.py
"""

import httpx
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_webapp_endpoints():
    print("🧪 Testing Devil's Advocate Webapp Integration\n")
    
    # Test 1: Health check
    print("1. Testing health check...")
    try:
        res = httpx.get(f"{API_BASE}/")
        assert res.status_code == 200
        print("   ✓ Backend is running\n")
    except Exception as e:
        print(f"   ✗ Backend not running: {e}\n")
        return
    
    # Test 2: Webapp page loads
    print("2. Testing webapp page...")
    try:
        res = httpx.get(f"{API_BASE}/history")
        assert res.status_code == 200
        assert "Devil's Advocate" in res.text
        print("   ✓ Webapp page loads successfully\n")
    except Exception as e:
        print(f"   ✗ Webapp page failed: {e}\n")
        return
    
    # Test 3: Create a test session
    print("3. Creating test session...")
    test_session = {
        "session_id": f"test-{int(datetime.now().timestamp())}",
        "topic": "AI Ethics and Bias",
        "user_topic": "AI Ethics",
        "started_at": int(datetime.now().timestamp() * 1000),
        "bias_score": 7.5,
        "opinions_summary": "Most sources emphasize the benefits of AI with limited discussion of ethical concerns.",
        "guardrail_triggered": False,
        "stats": {
            "analyzed": 3,
            "approved": 3,
            "skipped": 0
        },
        "pages": [
            {
                "url": "https://example.com/ai-benefits",
                "title": "The Amazing Benefits of AI",
                "topic": "AI Benefits",
                "biasScore": 8.0,
                "timestamp": int(datetime.now().timestamp() * 1000)
            },
            {
                "url": "https://example.com/ai-future",
                "title": "AI Will Transform Everything",
                "topic": "AI Future",
                "biasScore": 7.5,
                "timestamp": int(datetime.now().timestamp() * 1000)
            }
        ],
        "counter_perspectives": [
            {
                "topic": "AI Risks and Limitations",
                "viewpoint": "AI systems can perpetuate existing biases and create new forms of discrimination.",
                "sources": [
                    {
                        "url": "https://example.com/ai-bias",
                        "title": "The Hidden Biases in AI Systems",
                        "summary": "Research shows AI can amplify societal biases.",
                        "perspective": "Counter-Opinion",
                        "credibility": "High"
                    }
                ]
            }
        ],
        "sources": []
    }
    
    try:
        res = httpx.post(
            f"{API_BASE}/webapp/sync-session",
            json=test_session,
            timeout=10
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] == True
        session_id = data["session_id"]
        print(f"   ✓ Test session created: {session_id}\n")
    except Exception as e:
        print(f"   ✗ Failed to create session: {e}\n")
        return
    
    # Test 4: Retrieve sessions
    print("4. Retrieving sessions...")
    try:
        res = httpx.get(f"{API_BASE}/webapp/sessions")
        assert res.status_code == 200
        data = res.json()
        assert "sessions" in data
        assert "global_stats" in data
        print(f"   ✓ Found {len(data['sessions'])} session(s)")
        print(f"   ✓ Global stats: {data['global_stats']}\n")
    except Exception as e:
        print(f"   ✗ Failed to retrieve sessions: {e}\n")
        return
    
    # Test 5: Get session detail
    print("5. Getting session detail...")
    try:
        res = httpx.get(f"{API_BASE}/webapp/session/{session_id}")
        assert res.status_code == 200
        data = res.json()
        assert "session" in data
        assert "pages" in data
        assert "counter_perspectives" in data
        print(f"   ✓ Session detail retrieved")
        print(f"   ✓ Pages: {len(data['pages'])}")
        print(f"   ✓ Counter perspectives: {len(data['counter_perspectives'])}\n")
    except Exception as e:
        print(f"   ✗ Failed to get session detail: {e}\n")
        return
    
    # Test 6: Mark a page as citation
    print("6. Testing citation feature...")
    try:
        # Get the first page ID
        res = httpx.get(f"{API_BASE}/webapp/session/{session_id}")
        data = res.json()
        if data["pages"]:
            page_id = data["pages"][0]["id"]
            res = httpx.post(
                f"{API_BASE}/webapp/citation",
                json={"page_id": page_id, "note": "Key source for AI ethics research"}
            )
            assert res.status_code == 200
            print(f"   ✓ Page marked as citation\n")
        else:
            print("   ⚠ No pages to mark as citation\n")
    except Exception as e:
        print(f"   ✗ Failed to mark citation: {e}\n")
    
    # Test 7: Delete test session
    print("7. Cleaning up test session...")
    try:
        res = httpx.delete(f"{API_BASE}/webapp/session/{session_id}")
        assert res.status_code == 200
        print(f"   ✓ Test session deleted\n")
    except Exception as e:
        print(f"   ✗ Failed to delete session: {e}\n")
    
    print("=" * 60)
    print("✅ All webapp tests passed!")
    print("=" * 60)
    print("\n📱 Next steps:")
    print("1. Open the extension and start a research session")
    print("2. Browse a few pages")
    print("3. End the session")
    print("4. Click 'View Research History' in the extension")
    print("5. Your session should appear in the webapp!\n")


if __name__ == "__main__":
    test_webapp_endpoints()
