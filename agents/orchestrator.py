"""
Devil's Advocate — Lead Orchestrator
Coordinates the 4 sub-agents in a Sequential Pipeline and formats
the final response for the browser extension popup.

Pipeline: Gatekeeper → Mirror → Devil's Advocate → Librarian → Merge
"""

import json
import logging
from agents.base_agent import BaseAgent
from agents.session_integrity_agent import SessionIntegrityAgent
from agents.bias_auditor_agent import BiasAuditorAgent
from agents.counter_opinion_agent import CounterOpinionAgent
from agents.retrieval_verification_agent import RetrievalVerificationAgent

logger = logging.getLogger("orchestrator")

SYNTHESIS_PROMPT = """You are the Lead Orchestrator for Devil's Advocate.
Your mission is to dismantle confirmation bias."""


class Orchestrator(BaseAgent):
    """
    The Lead Orchestrator runs a Sequential Pipeline:
      1. SessionIntegrityAgent  → filters noise, extracts topic and vector
      2. BiasAuditorAgent       → calculates bias score, extracts theme
      3. CounterOpinionAgent    → generates counter-arguments / applies guardrail
      4. RetrievalVerificationAgent → fetches sources via SerpAPI
      5. Merge                  → pairs counter-topics with real links
    """

    def __init__(self):
        super().__init__(name="Orchestrator", system_prompt=SYNTHESIS_PROMPT)
        self.gatekeeper = SessionIntegrityAgent()
        self.mirror = BiasAuditorAgent()
        self.devils_advocate = CounterOpinionAgent()
        self.librarian = RetrievalVerificationAgent()

    def _merge_counter_perspectives(self, counter_topics: list, curated_links: list) -> list:
        """
        Merge counter-topics from Agent 3 with curated links from Agent 4.
        Each counter-perspective becomes a clickable item with a URL.

        Strategy: distribute opposing-perspective links across counter-topics,
        then attach any remaining links.
        """
        # Separate links by perspective
        opposing = [l for l in curated_links if self._is_opposing(l.get("perspective", ""))]
        inline = [l for l in curated_links if not self._is_opposing(l.get("perspective", ""))]

        merged = []
        for i, ct in enumerate(counter_topics):
            perspective = {
                "topic": ct.get("topic", "Unknown"),
                "viewpoint": ct.get("alternative_viewpoint", ""),
                "sources": []
            }
            # Assign opposing links round-robin to counter-topics
            if opposing:
                link = opposing.pop(0)
                perspective["sources"].append({
                    "title": link.get("title", "Source"),
                    "url": link.get("url", "#"),
                    "summary": link.get("summary", ""),
                    "credibility": link.get("credibility", "Medium")
                })
            merged.append(perspective)

        # If there are leftover opposing links, distribute to existing topics
        for i, link in enumerate(opposing):
            idx = i % len(merged) if merged else 0
            if merged:
                merged[idx]["sources"].append({
                    "title": link.get("title", "Source"),
                    "url": link.get("url", "#"),
                    "summary": link.get("summary", ""),
                    "credibility": link.get("credibility", "Medium")
                })

        return merged

    def _is_opposing(self, perspective: str) -> bool:
        p = perspective.lower()
        return "counter" in p or "opposing" in p or "dissent" in p

    def run(self, text: str, url: str, session_topic: str = "") -> dict:
        # ── Agent 1: Gatekeeper ─────────────────────────────────────
        logger.info("Running Gatekeeper...")
        try:
            gatekeeper_output = self.gatekeeper.run(text, url, session_topic)
        except Exception as e:
            logger.error("Gatekeeper failed: %s", e)
            return {
                "error": True,
                "synthesis": f"Analysis Failed — Gatekeeper error: {e}"
            }
        
        if gatekeeper_output.get("status") != "ACCEPTED":
            return {
                "error": True,
                "gatekeeper": gatekeeper_output,
                "synthesis": f"Research Paused — {gatekeeper_output.get('reason')}"
            }

        topic = gatekeeper_output.get("overarching_topic", "Unknown")
        logger.info("Gatekeeper ACCEPTED topic: %s", topic)

        # ── Agent 2: Mirror ─────────────────────────────────────────
        logger.info("Running Bias Auditor...")
        try:
            mirror_output = self.mirror.run(text, topic, session_topic)
        except Exception as e:
            logger.error("Mirror failed: %s", e)
            mirror_output = {
                "cumulative_bias_score": 5.0,
                "research_theme": topic,
                "opinions_summary": "Unable to analyze bias at this time.",
                "feedback_prompt": ""
            }

        logger.info("Bias Score: %s", mirror_output.get("cumulative_bias_score"))

        # ── Agent 3: Devil's Advocate ───────────────────────────────
        logger.info("Running Counter-Opinion Architect...")
        try:
            da_output = self.devils_advocate.run(mirror_output)
        except Exception as e:
            logger.error("Counter-Opinion failed: %s", e)
            da_output = {
                "null_guardrail": "None",
                "counter_topics": []
            }

        # ── Agent 4: Librarian ──────────────────────────────────────
        logger.info("Running Retrieval & Verification...")
        try:
            librarian_output = self.librarian.run(da_output, topic=mirror_output.get("research_theme", ""))
        except Exception as e:
            logger.error("Librarian failed: %s", e)
            librarian_output = {
                "curated_links": [],
                "note": f"Search failed: {e}"
            }

        logger.info("Found %d curated links", len(librarian_output.get("curated_links", [])))

        # ── Merge: pair counter-topics with real links ──────────────
        counter_topics = da_output.get("counter_topics", [])
        curated_links = librarian_output.get("curated_links", [])
        guardrail = da_output.get("null_guardrail", "None")

        counter_perspectives = []
        guardrail_triggered = "NO_CREDIBLE_DISSENT_FOUND" in str(guardrail)

        if not guardrail_triggered and counter_topics:
            counter_perspectives = self._merge_counter_perspectives(counter_topics, curated_links)

        # Build synthesis text
        bias_score = mirror_output.get("cumulative_bias_score", 5.0)
        bias_label = "Echo Chamber" if bias_score >= 7 else "Moderate" if bias_score >= 4 else "Balanced"
        synthesis = f"Topic: {topic} | Bias: {bias_score}/10 ({bias_label}) | {len(counter_perspectives)} counter-perspectives"

        return {
            "error": False,
            "gatekeeper": gatekeeper_output,
            "mirror": mirror_output,
            "devils_advocate": da_output,
            "librarian": librarian_output,
            "counter_perspectives": counter_perspectives,
            "guardrail_triggered": guardrail_triggered,
            "synthesis": synthesis,
        }
