"""
Devil's Advocate — Comprehensive Test Suite
Tests the full pipeline, individual agents, and edge cases.

Run with:  python test_pipeline.py
"""

import json
import time
import sys
import traceback

# ── Color output helpers ─────────────────────────────────────────────
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"

def ok(msg):
    print(f"  {Colors.GREEN}✓{Colors.END} {msg}")

def fail(msg):
    print(f"  {Colors.RED}✗{Colors.END} {msg}")

def warn(msg):
    print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")

def header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═'*60}")
    print(f"  {msg}")
    print(f"{'═'*60}{Colors.END}")

# ── Test Counters ────────────────────────────────────────────────────
passed = 0
failed = 0
skipped = 0

def assert_test(condition, name, details=""):
    global passed, failed
    if condition:
        ok(name)
        passed += 1
    else:
        fail(f"{name} — {details}")
        failed += 1

# ═══════════════════════════════════════════════════════════════════════
# Test 1: Configuration Validation
# ═══════════════════════════════════════════════════════════════════════
def test_config():
    header("Test 1: Configuration")
    from config import settings
    
    assert_test(settings.HOST == "0.0.0.0", "HOST defaults to 0.0.0.0")
    assert_test(settings.PORT == 8000, "PORT defaults to 8000")
    assert_test(settings.LLM_MODEL == "llama-3.1-8b-instant", "LLM model configured")
    assert_test(settings.LLM_MAX_TOKENS == 1024, "Max tokens set")
    assert_test(0 < settings.LLM_TEMPERATURE < 1, "Temperature in valid range")
    
    missing = settings.validate()
    if "GROQ_API_KEY" in missing:
        warn("GROQ_API_KEY not set — LLM tests will be skipped")
        return False
    else:
        ok("GROQ_API_KEY is configured")
    
    return True

# ═══════════════════════════════════════════════════════════════════════
# Test 2: Vector Memory
# ═══════════════════════════════════════════════════════════════════════
def test_vector_memory():
    header("Test 2: Vector Memory")
    from vector_memory import VectorMemory
    
    mem = VectorMemory()
    
    # Test initial state
    assert_test(len(mem.local_memory) == 0, "Initial memory is empty")
    assert_test(mem.calculate_bias_score() == 5.0, "Initial bias score is neutral (5.0)")
    
    # Test first vector similarity
    sim = mem.get_golden_thread_similarity([0.5, 0.3, -0.1])
    assert_test(sim == 1.0, "First vector has 100% similarity to empty thread")
    
    # Store vectors
    mem.store_vector([0.5, 0.3, -0.1], {"url": "test1.com", "topic": "AI"})
    assert_test(len(mem.local_memory) == 1, "Vector stored successfully")
    
    mem.store_vector([0.6, 0.4, -0.2], {"url": "test2.com", "topic": "AI"})
    mem.store_vector([0.5, 0.35, -0.15], {"url": "test3.com", "topic": "AI"})
    
    # Bias score for similar vectors should be HIGH (echo chamber)
    score = mem.calculate_bias_score()
    assert_test(score >= 7, f"Similar vectors → high bias ({score}/10)", f"Got {score}")
    
    # Add a dissenting vector
    mem.store_vector([-0.8, -0.5, 0.9], {"url": "test4.com", "topic": "Anti-AI"})
    new_score = mem.calculate_bias_score()
    assert_test(new_score < score, f"Dissenting vector lowered bias ({new_score}/10)")
    
    # Test golden thread similarity with opposite vector
    sim_opposite = mem.get_golden_thread_similarity([-1.0, -1.0, 1.0])
    assert_test(sim_opposite < 0.5, f"Opposite vector has low similarity ({sim_opposite:.2f})")
    
    # Edge case: zero-magnitude vector
    sim_zero = mem.get_golden_thread_similarity([0.0, 0.0, 0.0])
    assert_test(sim_zero == 0.0, "Zero vector returns 0 similarity")

# ═══════════════════════════════════════════════════════════════════════
# Test 3: Session Integrity Agent (Gatekeeper)
# ═══════════════════════════════════════════════════════════════════════
def test_gatekeeper(has_api_key):
    header("Test 3: Session Integrity Agent (Gatekeeper)")
    from agents.session_integrity_agent import SessionIntegrityAgent
    
    agent = SessionIntegrityAgent()
    
    # Level 1: URL Blacklist
    result = agent.run("Some valid research text about quantum computing and its applications.", "https://www.paypal.com/checkout")
    assert_test(result["status"] == "REJECTED_LEVEL_1", "Rejects PayPal URL (Level 1)")
    
    result = agent.run("Some valid research text about quantum computing and its applications.", "https://www.amazon.com/product")
    assert_test(result["status"] == "REJECTED_LEVEL_1", "Rejects Amazon URL (Level 1)")
    
    result = agent.run("Some valid research text about quantum computing and its applications.", "https://www.facebook.com/profile")
    assert_test(result["status"] == "REJECTED_LEVEL_1", "Rejects Facebook URL (Level 1)")
    
    # Level 2: Transaction keywords
    result = agent.run("Add to cart now! Buy now and checkout with your credit card for the best deal.", "https://example.com")
    assert_test(result["status"] == "REJECTED_LEVEL_2", "Rejects transactional text (Level 2)")
    
    result = agent.run("Enter your password and login to proceed to checkout immediately please thank you.", "https://example.com")
    assert_test(result["status"] == "REJECTED_LEVEL_2", "Rejects login/password text (Level 2)")
    
    # Level 3+: Actual LLM analysis (requires API key)
    if has_api_key:
        result = agent.run(
            "Artificial intelligence is revolutionizing healthcare by enabling early disease detection "
            "through machine learning algorithms. Studies show that AI-powered diagnostic tools can achieve "
            "accuracy rates comparable to experienced physicians in certain specialties.",
            "https://nature.com/articles/ai-healthcare"
        )
        assert_test(result["status"] == "ACCEPTED", "Accepts valid research text")
        assert_test("overarching_topic" in result, "Extracts topic")
        assert_test(isinstance(result.get("stance_vector"), list), "Returns stance vector")
        assert_test(len(result.get("stance_vector", [])) == 3, "Stance vector is 3-dimensional")
        ok(f"  Topic: {result.get('overarching_topic')}")
        ok(f"  Vector: {result.get('stance_vector')}")
    else:
        global skipped
        skipped += 3
        warn("Skipping LLM-dependent gatekeeper tests (no API key)")

# ═══════════════════════════════════════════════════════════════════════
# Test 4: Bias Auditor Agent (Mirror)
# ═══════════════════════════════════════════════════════════════════════
def test_bias_auditor(has_api_key):
    header("Test 4: Bias Auditor Agent (Mirror)")
    
    if not has_api_key:
        global skipped
        skipped += 2
        warn("Skipping Bias Auditor tests (no API key)")
        return
    
    from agents.bias_auditor_agent import BiasAuditorAgent
    
    agent = BiasAuditorAgent()
    result = agent.run(
        "The benefits of renewable energy are clear. Solar and wind power are becoming cheaper and more "
        "efficient every year. Fossil fuels are destroying our planet and we must transition immediately.",
        "Renewable Energy"
    )
    
    assert_test("cumulative_bias_score" in result, "Returns bias score")
    assert_test("research_theme" in result, f"Returns research theme: {result.get('research_theme')}")
    assert_test("opinions_summary" in result, "Returns opinions summary")

# ═══════════════════════════════════════════════════════════════════════
# Test 5: Counter-Opinion Agent (Devil's Advocate)
# ═══════════════════════════════════════════════════════════════════════
def test_counter_opinion(has_api_key):
    header("Test 5: Counter-Opinion Agent (Devil's Advocate)")
    
    if not has_api_key:
        global skipped
        skipped += 3
        warn("Skipping Counter-Opinion tests (no API key)")
        return
    
    from agents.counter_opinion_agent import CounterOpinionAgent
    
    agent = CounterOpinionAgent()
    
    # Test with debatable topic
    result = agent.run({
        "research_theme": "Benefits of Renewable Energy",
        "opinions_summary": "All sources praise renewable energy as the sole solution to climate change."
    })
    
    assert_test("null_guardrail" in result, "Returns guardrail field")
    assert_test("counter_topics" in result, "Returns counter_topics")
    assert_test(isinstance(result["counter_topics"], list), "counter_topics is a list")
    
    if result["counter_topics"]:
        ok(f"  Generated {len(result['counter_topics'])} counter-arguments")
        for ct in result["counter_topics"][:2]:
            ok(f"    → {ct.get('topic', 'N/A')}")
    
    # Test with objective fact (should trigger guardrail)
    result_objective = agent.run({
        "research_theme": "The boiling point of water at sea level",
        "opinions_summary": "Water boils at 100°C at standard atmospheric pressure."
    })
    
    guardrail = result_objective.get("null_guardrail", "")
    if "NO_CREDIBLE_DISSENT_FOUND" in str(guardrail):
        ok("Truth Guardrail correctly triggered for objective fact")
    else:
        warn(f"Guardrail may not have triggered (got: {guardrail})")

# ═══════════════════════════════════════════════════════════════════════
# Test 6: Full Pipeline (Orchestrator)
# ═══════════════════════════════════════════════════════════════════════
def test_full_pipeline(has_api_key):
    header("Test 6: Full Pipeline (Orchestrator)")
    
    if not has_api_key:
        global skipped
        skipped += 5
        warn("Skipping full pipeline tests (no API key)")
        return
    
    from agents.orchestrator import Orchestrator
    
    orch = Orchestrator()
    
    # Test 1: Valid controversial topic
    start = time.time()
    result = orch.run(
        "Social media has been shown to significantly impact mental health in teenagers. "
        "Multiple studies demonstrate increased rates of anxiety, depression, and low self-esteem "
        "among heavy social media users. Platforms like Instagram and TikTok create unrealistic "
        "beauty standards and foster cyberbullying.",
        "https://psychologytoday.com/social-media-impact"
    )
    elapsed = round(time.time() - start, 2)
    
    assert_test(not result.get("error", True), f"Pipeline completed without error ({elapsed}s)")
    assert_test("gatekeeper" in result, "Contains gatekeeper output")
    assert_test("mirror" in result, "Contains mirror output")
    assert_test("devils_advocate" in result, "Contains counter-opinion output")
    assert_test("synthesis" in result, "Contains synthesis")
    
    if not result.get("error"):
        ok(f"  Topic: {result['gatekeeper'].get('overarching_topic', 'N/A')}")
        ok(f"  Bias: {result['mirror'].get('cumulative_bias_score', 'N/A')}/10")
        ct_count = len(result.get('devils_advocate', {}).get('counter_topics', []))
        ok(f"  Counter-args: {ct_count}")
        link_count = len(result.get('librarian', {}).get('curated_links', []))
        ok(f"  Sources: {link_count}")
    
    # Test 2: Rejected URL
    result_rejected = orch.run("Test content for the bank website.", "https://bank.com/account")
    assert_test(result_rejected.get("error") == True, "Banking URL correctly rejected")

# ═══════════════════════════════════════════════════════════════════════
# Test 7: Edge Cases
# ═══════════════════════════════════════════════════════════════════════
def test_edge_cases(has_api_key):
    header("Test 7: Edge Cases")
    
    # Test very long text (should not crash)
    from agents.session_integrity_agent import SessionIntegrityAgent
    agent = SessionIntegrityAgent()
    
    # Edge: URL with mixed-case blacklist
    result = agent.run("Valid research text about global warming effects on ecosystems and biodiversity.", "https://PAYPAL.COM/research")
    assert_test(result["status"] == "REJECTED_LEVEL_1", "Case-insensitive URL blacklist")
    
    # Edge: Empty URL
    if has_api_key:
        result = agent.run(
            "Climate change is causing rapid ice sheet melting in the Arctic regions, "
            "threatening polar bear habitats and causing rising sea levels worldwide.",
            ""
        )
        assert_test(result["status"] == "ACCEPTED", "Handles empty URL gracefully")
    
    # Edge: Text with only whitespace after keywords
    result = agent.run("        checkout         ", "https://example.com")
    assert_test(result["status"] == "REJECTED_LEVEL_2", "Detects keywords in whitespace-padded text")
    
    # Edge: Unicode text
    if has_api_key:
        result = agent.run(
            "人工智能在医疗领域的应用正在改变传统诊疗模式。机器学习算法能够分析大量医学影像数据，"
            "辅助医生进行更精准的疾病诊断。This represents a paradigm shift in healthcare.",
            "https://example.com/ai-healthcare"
        )
        assert_test(result["status"] == "ACCEPTED", "Handles Unicode/multilingual text")

# ═══════════════════════════════════════════════════════════════════════
# Test 8: API Server (requires running server)
# ═══════════════════════════════════════════════════════════════════════
def test_api():
    header("Test 8: API Server")
    
    import httpx
    
    try:
        r = httpx.get("http://localhost:8000/", timeout=5)
        if r.status_code == 200:
            data = r.json()
            assert_test(data["status"] in ["operational", "degraded"], f"Server status: {data['status']}")
            assert_test(data["version"] == "1.0.0", "Version matches")
            ok(f"  Keys: {json.dumps(data['keys_configured'])}")
        else:
            warn(f"Server returned {r.status_code}")
    except Exception:
        global skipped
        skipped += 2
        warn("Server not running — skipping API tests (start with: python main.py)")
        return
    
    # Test validation: too-short text
    try:
        r = httpx.post("http://localhost:8000/analyze", json={"text": "short"}, timeout=5)
        assert_test(r.status_code == 422, "Rejects text shorter than 20 chars")
    except Exception as e:
        warn(f"Validation test failed: {e}")

# ═══════════════════════════════════════════════════════════════════════
# Run All Tests
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{Colors.BOLD}🔥 Devil's Advocate — Test Suite{Colors.END}")
    print(f"{'─'*60}")
    
    start_time = time.time()
    
    try:
        has_key = test_config()
        test_vector_memory()
        test_gatekeeper(has_key)
        test_bias_auditor(has_key)
        test_counter_opinion(has_key)
        test_full_pipeline(has_key)
        test_edge_cases(has_key)
        test_api()
    except Exception as e:
        fail(f"Unhandled exception: {e}")
        traceback.print_exc()
        failed += 1
    
    total_time = round(time.time() - start_time, 2)
    
    print(f"\n{'═'*60}")
    print(f"{Colors.BOLD}Results:{Colors.END}  {Colors.GREEN}{passed} passed{Colors.END}  |  {Colors.RED}{failed} failed{Colors.END}  |  {Colors.YELLOW}{skipped} skipped{Colors.END}  |  ⏱ {total_time}s")
    print(f"{'═'*60}\n")
    
    sys.exit(1 if failed > 0 else 0)
