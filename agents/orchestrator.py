"""
Devil's Advocate — Lead Orchestrator
Coordinates the 4 sub-agents in a Sequential Pipeline and formats
the final response for the browser extension popup.

Pipeline: Gatekeeper → Mirror → Devil's Advocate → Librarian → Synthesis
"""

import json
from agents.base_agent import BaseAgent
from agents.session_integrity_agent import SessionIntegrityAgent
from agents.bias_auditor_agent import BiasAuditorAgent
from agents.counter_opinion_agent import CounterOpinionAgent
from agents.retrieval_verification_agent import RetrievalVerificationAgent

SYNTHESIS_PROMPT = """You are the Lead Orchestrator for Devil's Advocate.
Your mission is to dismantle confirmation bias.

You will receive a complete analysis package containing:
1. Agent 1 (Gatekeeper): Verified topic and summary.
2. Agent 2 (Mirror): Bias score and summary of opinions so far.
3. Agent 3 (Devil's Advocate): Counter-topics (or a Truth Guardrail if none exist).
4. Agent 4 (Librarian): Curated real-world links for counter-opinions and inline topics.

Your job is to produce a FINAL RESPONSE with these clear sections:

## 1. The Mirror (Your Research Trajectory)
Summarize what the user has learned so far and display the Cumulative Bias Score (mention if it's an Echo Chamber or Balanced).

## 2. The Devil's Advocate
If the Truth-Gating Guardrail was triggered (NO_CREDIBLE_DISSENT_FOUND), clearly state that the topic is largely objective or lacks credible dissent, and prioritize accuracy over forced variety.
Otherwise, present the strongest counter-topics identified.

## 3. The Librarian's Curated Sources
List the retrieved links from Agent 4. For each link, provide the Title (as a Markdown link), the perspective (Neutral, Opposing, or Inline), and a brief summary of what it adds to the conversation.

Write in a clear, engaging tone. Use bullet points and headers.
IMPORTANT: Your response should be in well-formatted Markdown."""


class Orchestrator(BaseAgent):
    """
    The Lead Orchestrator runs a Sequential Pipeline:
      1. SessionIntegrityAgent  → filters noise, extracts topic and vector
      2. BiasAuditorAgent       → calculates bias score, extracts theme
      3. CounterOpinionAgent    → generates counter-arguments / applies guardrail
      4. RetrievalVerificationAgent → fetches sources via SerpAPI
      5. Synthesis              → formats final response
    """

    def __init__(self):
        super().__init__(name="Orchestrator", system_prompt=SYNTHESIS_PROMPT)
        self.gatekeeper = SessionIntegrityAgent()
        self.mirror = BiasAuditorAgent()
        self.devils_advocate = CounterOpinionAgent()
        self.librarian = RetrievalVerificationAgent()

    def run(self, text: str, url: str) -> dict:
        # ── Agent 1: Gatekeeper ─────────────────────────────────────
        gatekeeper_output = self.gatekeeper.run(text, url)
        
        if gatekeeper_output.get("status") != "ACCEPTED":
            return {
                "error": True,
                "synthesis": f"⚠️ **Research Paused**\n\nThe Gatekeeper rejected this page: {gatekeeper_output.get('reason')}"
            }

        topic = gatekeeper_output.get("overarching_topic", "Unknown")

        # ── Agent 2: Mirror ─────────────────────────────────────────
        mirror_output = self.mirror.run(text, topic)

        # ── Agent 3: Devil's Advocate ───────────────────────────────
        da_output = self.devils_advocate.run(mirror_output)

        # ── Agent 4: Librarian ──────────────────────────────────────
        librarian_output = self.librarian.run(da_output)

        # ── Synthesis: Format final response ────────────────────────
        synthesis_input = (
            f"=== AGENT 1 (GATEKEEPER) ===\n{json.dumps(gatekeeper_output, indent=2)}\n\n"
            f"=== AGENT 2 (MIRROR) ===\n{json.dumps(mirror_output, indent=2)}\n\n"
            f"=== AGENT 3 (DEVIL'S ADVOCATE) ===\n{json.dumps(da_output, indent=2)}\n\n"
            f"=== AGENT 4 (LIBRARIAN) ===\n{json.dumps(librarian_output, indent=2)}\n\n"
            "Now synthesize the final Devil's Advocate response."
        )
        synthesis = self._call_llm(synthesis_input, temperature=0.5)

        return {
            "error": False,
            "gatekeeper": gatekeeper_output,
            "mirror": mirror_output,
            "devils_advocate": da_output,
            "librarian": librarian_output,
            "synthesis": synthesis,
        }
