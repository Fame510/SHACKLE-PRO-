"""
SHACKLE Guard — Self-contained proof of concept.

Demonstrates all four circuit breaker triggers without requiring
CrewAI, LangGraph, or AutoGen. Uses mock infrastructure to simulate
the exact failure modes SHACKLE targets.

Usage:
    pip install rich
    python demo.py

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

BY USING THIS SOFTWARE, YOU ACKNOWLEDGE THAT LLM ORCHESTRATION IS INHERENTLY
NON-DETERMINISTIC. SHACKLE IS A BEST-EFFORT CIRCUIT BREAKER AND DOES NOT
GUARANTEE PREVENTING ALL API SPEND OVERRUNS. YOU REMAIN SOLELY RESPONSIBLE FOR
MONITORING YOUR OWN API LIMITS AND USAGE BILLS.
"""

import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shackle import Guard
from shackle.core import TriggerEngine, ShackleInterrupt, ExecutionState, render_hitl_terminal


# ─────────────────────────────────────────────────────────────────────────
# MOCK TOOLS — no API keys required
# ─────────────────────────────────────────────────────────────────────────

class FailingTool:
    """Simulates a tool that always returns an error — causing retry loops."""
    name = "web_search"
    def run(self, query: str) -> str:
        return f"Error: upstream API timeout for query='{query}'"


class ExpensiveAnalyzer:
    """Simulates a tool that succeeds but burns tokens."""
    name = "document_analyzer"
    def run(self, query: str) -> str:
        return "Analysis complete (but we burned tokens)"


class SlowAPITool:
    """Simulates a hung external API."""
    name = "slow_api"
    def run(self, query: str) -> str:
        time.sleep(3.0)
        return "finally done"


# ─────────────────────────────────────────────────────────────────────────
# SCENARIO 1: LOOP OF DEATH
# Simulates: CrewAI Issue #737 / AutoGen Issue #108
# ─────────────────────────────────────────────────────────────────────────

def scenario_1_loop_of_death():
    print("=" * 65)
    print(" SHACKLE DEMO — Scenario 1: Loop of Death")
    print(" Simulates: CrewAI #737 / AutoGen #108 — agent retries")
    print(" the same failing tool with identical input forever")
    print("=" * 65)

    engine = TriggerEngine(
        budget=100.0,          # high enough not to trip
        max_repeat_calls=3,    # trip on 3rd identical call
        timeout_seconds=60,
        max_tool_calls=50,
    )
    state = ExecutionState()
    tool = FailingTool()

    print(f"\n[AGENT] Starting task: 'latest AI safety research'")
    print(f"[AGENT] (Simulating a CrewAI execution loop)\n")

    for i in range(20):
        print(f"[AGENT] Iteration {i + 1}: deciding to call '{tool.name}'")

        # Track LLM cost
        try:
            engine.evaluate_llm_call("gpt-4o", 2500, 300, state)
        except ShackleInterrupt as si:
            print(f"\n⛓️  BUDGET TRIPPED: {si.trigger_type}")
            break

        # Evaluate tool call — this is where the loop gets caught
        try:
            engine.evaluate_tool_call("ResearchAgent", tool.name, "latest AI safety research", state)
        except ShackleInterrupt as si:
            print(f"\n⛓️  SHACKLE CIRCUIT BREAKER: {si.trigger_type}")
            print(f"   Tool: {si.details['tool']}")
            print(f"   Call count: {si.details['call_count']}")
            print(f"   Cost so far: ${state.total_cost:.5f}")
            print(f"   Time elapsed: {time.time() - state.start_time:.1f}s")
            print("\n   [In production: interactive CLI menu appears here]")
            print("   [Operator would press A=Abort, S=Skip, R=Resume]\n")
            break

        result = tool.run("latest AI safety research")
        print(f"[TOOL] Result: {result}")
        print(f"[AGENT] Got an error. Retrying same input...\n")
        time.sleep(0.2)

    print(f"\n✅ Scenario 1 complete — loop caught after 3 repetitions")
    print(f"   Total spend: ${state.total_cost:.5f} (vs unbounded without SHACKLE)\n")


# ─────────────────────────────────────────────────────────────────────────
# SCENARIO 2: BUDGET EXCEEDED
# ─────────────────────────────────────────────────────────────────────────

def scenario_2_budget_breach():
    print("=" * 65)
    print(" SHACKLE DEMO — Scenario 2: Budget Guard")
    print(" Simulates: CrewAI Discussion #4232 — agent burns budget")
    print("=" * 65)

    engine = TriggerEngine(
        budget=0.002,          # $0.002 limit — very tight
        max_repeat_calls=10,
        timeout_seconds=60,
    )
    state = ExecutionState()

    print(f"\n[AGENT] Running with ${engine.budget:.4f} budget on Claude Sonnet")
    print("[AGENT] One Sonnet call at 500 input + 200 output = ~$0.0045\n")

    try:
        # One Claude Sonnet call with 500 input + 200 output tokens
        # At $3/$15 per MTok: (500*3 + 200*15) / 1M = $0.0045 > $0.002 budget
        engine.evaluate_llm_call("claude-3-5-sonnet", 500, 200, state)
        print("[AGENT] LLM call completed (shouldn't reach here)")
    except ShackleInterrupt as si:
        print(f"⛓️  BUDGET BREACHED: Spent ${state.total_cost:.5f} (limit: ${engine.budget:.4f})")
        print(f"   Tokens used: {state.input_tokens} in / {state.output_tokens} out")
        print(f"   Trigger: {si.trigger_type}\n")

    print("✅ Scenario 2 complete — budget guard prevented overspend\n")


# ─────────────────────────────────────────────────────────────────────────
# SCENARIO 3: EXECUTION TIMEOUT
# ─────────────────────────────────────────────────────────────────────────

def scenario_3_timeout():
    print("=" * 65)
    print(" SHACKLE DEMO — Scenario 3: Execution Timeout")
    print(" Simulates: AutoGen Issue #321 — agent hangs on slow API")
    print("=" * 65)

    engine = TriggerEngine(
        budget=100.0,
        max_repeat_calls=10,
        timeout_seconds=0.001,  # 1ms — trips immediately
    )
    state = ExecutionState()
    time.sleep(0.01)  # ensure we're past the timeout

    print(f"\n[AGENT] Running with {engine.timeout_seconds}s timeout")
    print("[AGENT] Attempting tool call on a hung API...\n")

    try:
        engine.evaluate_tool_call("DataAgent", "slow_api", "query data", state)
        print("[AGENT] Tool call completed (shouldn't reach here)")
    except ShackleInterrupt as si:
        print(f"⛓️  TIMEOUT: {si.details['elapsed_seconds']:.3f}s elapsed (limit: {engine.timeout_seconds}s)")
        print(f"   Trigger: {si.trigger_type}\n")

    print("✅ Scenario 3 complete — timeout prevented hung execution\n")


# ─────────────────────────────────────────────────────────────────────────
# SCENARIO 4: THE GUARD DECORATOR (production pattern)
# ─────────────────────────────────────────────────────────────────────────

def scenario_4_guard_decorator():
    print("=" * 65)
    print(" SHACKLE DEMO — Scenario 4: @Guard Decorator (Production)")
    print("=" * 65)

    @Guard(budget=100.0, max_repeat_calls=3, timeout_seconds=60)
    def my_safe_agent():
        """Your actual agent logic goes here."""
        print("[AGENT] Executing production workflow...")
        print("[AGENT] In a real run, SHACKLE patches litellm + BaseTool")
        print("[AGENT] automatically — no manual trigger calls needed.")
        time.sleep(0.2)
        return {"status": "success", "output": "workflow complete"}

    result = my_safe_agent()
    print(f"\n✅ Guard decorator returned: {result}")
    print("   All patches applied and cleaned up automatically.\n")


# ─────────────────────────────────────────────────────────────────────────
# INTEGRATION EXAMPLES
# ─────────────────────────────────────────────────────────────────────────

def print_examples():
    print("=" * 65)
    print(" REAL CREWAI INTEGRATION (copy-paste ready)")
    print("=" * 65)
    print('''
# Your existing CrewAI code — UNCHANGED
from crewai import Agent, Task, Crew
from shackle import Guard

researcher = Agent(
    role="Researcher",
    goal="Find information",
    backstory="Expert researcher",
    tools=[search_web],
    llm="gpt-4o"
)

crew = Crew(agents=[researcher], tasks=[...])

# ── Add SHACKLE: one decorator, zero other changes ───
@Guard(budget=0.10, max_repeat_calls=3, timeout_seconds=120)
def safe_run():
    return crew.kickoff()

result = safe_run()
''')
    print("Demo complete. Source: github.com/Fame510/SHACKLE-PRO\n")


# ─────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scenario_1_loop_of_death()
    scenario_2_budget_breach()
    scenario_3_timeout()
    scenario_4_guard_decorator()
    print_examples()
