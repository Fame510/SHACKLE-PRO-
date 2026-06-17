# SHACKLE $2,500 Service - Delivery Process

Internal workflow for delivering professional SHACKLE implementation service.

---

## 📋 STAGE 1: PAYMENT RECEIVED

### When Stripe Notification Arrives:

**Within 24 hours, send this email:**

```
Subject: SHACKLE Implementation - Next Steps

Hi [Name],

Thanks for your payment! Here's what happens next:

1. CONFIDENTIALITY AGREEMENT
Please review and sign the attached NDA (NDA.md).
This protects both your code and our integration process.
You can sign electronically - just fill in your details at the bottom
and reply with the signed PDF.

2. SERVICE AGREEMENT
Attached is your Service Agreement. Your payment confirms acceptance
of these terms. Keep this for your records.

3. SEND YOUR CODE (After NDA is signed)
Reply with:
- GitHub repo URL (preferred) OR zip file of your code
- Brief description of your agent's purpose (2-3 sentences)
- Any known cost/loop issues you've experienced
- Framework(s) you're using (CrewAI, LangGraph, AutoGen, etc.)

4. DELIVERY TIMELINE
Within 48-72 hours of receiving your code, you'll get:
- Architecture audit report (PDF)
- Custom SHACKLE configuration file
- Step-by-step integration guide

5. 30-DAY SUPPORT
Email support starts from the delivery date.
docspoc101@gmail.com - response within 48 business hours.

Questions? Just reply to this email.

Best,
Dante Bullock
Sovereign Logic
docspoc101@gmail.com
```

**Attachments:**
- NDA.md (converted to PDF)
- SERVICE-AGREEMENT.md (converted to PDF)

---

### Record Keeping:

Create folder structure:
```bash
mkdir -p ~/clients/[client-name]/{code,deliverables,correspondence}
```

Track in spreadsheet or text file:
```
Client: [Name]
Company: [Company]
Email: [Email]
Payment Date: [Date]
Stripe ID: [Transaction ID]
NDA Signed: [Date or Pending]
Code Received: [Date or Pending]
Delivered: [Date or Pending]
Support Ends: [30 days from delivery]
Status: [Waiting for NDA / In Progress / Delivered / Complete]
```

---

## 📋 STAGE 2: NDA SIGNED, AWAITING CODE

### When Client Returns Signed NDA:

**Send confirmation:**

```
Subject: Re: SHACKLE Implementation - NDA Received

Hi [Name],

NDA received and filed. You're all set to send your code.

Please reply with:
- GitHub repo URL (grant read access to: Fame510) OR
- Zip file of your complete codebase

Plus:
- Brief description of what your agent does
- Any known loop/cost issues
- Framework(s) used (CrewAI, LangGraph, AutoGen, etc.)

Once I receive your code, I'll begin the audit immediately.
You'll have your deliverables within 48-72 hours.

Best,
Dante
```

**Save signed NDA:**
```bash
cp signed-nda.pdf ~/clients/[client-name]/NDA-signed.pdf
```

---

## 📋 STAGE 3: CODE RECEIVED - ANALYSIS BEGINS

### When Client Sends Code:

**Immediate confirmation:**

```
Subject: Re: SHACKLE Implementation - Code Received

Hi [Name],

Code received. Analysis is now in progress.

You'll receive your deliverables within 48-72 hours:
- Architecture audit report
- Custom SHACKLE configuration
- Integration guide

I'll email you as soon as they're ready.

Best,
Dante
```

### Save Code:
```bash
# If GitHub repo:
cd ~/clients/[client-name]/code/
git clone [repo-url]

# If zip file:
unzip code.zip -d ~/clients/[client-name]/code/
```

### Set Reminder:
Mark calendar: Deliverables due in 48-72 hours (by [specific date/time])

---

## 📋 STAGE 4: PERFORM ANALYSIS

### Systematic Code Review Process:

#### Step 1: Repository Structure Analysis
```bash
cd ~/clients/[client-name]/code/[repo-name]
tree -L 3 > ../structure.txt
find . -name "*.py" | wc -l  # Count Python files
```

#### Step 2: Identify Agent Framework
Search for imports:
```bash
grep -r "from crewai" .
grep -r "from langgraph" .
grep -r "from autogen" .
grep -r "import crew" .
```

#### Step 3: Find Agent Initialization Points
Look for:
- `Crew(` or `crew =`
- `Graph(` or `graph =`
- `.kickoff()` calls
- `.invoke()` calls
- `agent.run()` or similar

#### Step 4: Identify Tools and LLM Calls
```bash
grep -r "BaseTool\|@tool\|Tool(" .
grep -r "ChatOpenAI\|ChatAnthropic\|litellm" .
```

#### Step 5: Analyze Loop Vulnerabilities
Look for:
- Tools called without error handling
- Retry logic without limits
- API calls in loops
- Missing timeout configurations

#### Step 6: Review Configuration Files
```bash
find . -name "*.env*" -o -name "*.yaml" -o -name "*.json" -o -name "config.py"
```

---

### Create Deliverables:

#### 1. Architecture Audit Report

Create: `~/clients/[client-name]/deliverables/Architecture-Audit.pdf`

**Template:**

```markdown
# SHACKLE Architecture Audit Report
**Client:** [Name/Company]
**Date:** [Date]
**Auditor:** Dante Bullock, Sovereign Logic

## Executive Summary
[2-3 paragraphs summarizing key findings]

## Codebase Overview
- **Framework:** CrewAI / LangGraph / AutoGen
- **Python Version:** [version]
- **LLM Provider:** OpenAI / Anthropic / Other
- **Total Python Files:** [count]
- **Agent Entry Points:** [count]

## Identified Vulnerabilities

### 1. Loop Risk: [Tool/Function Name]
**Location:** `[file.py:line]`
**Risk Level:** High / Medium / Low
**Description:** [What could go wrong]
**Impact:** [Token cost estimate if loop occurs]

### 2. [Additional vulnerabilities...]

## Token Usage Analysis
**Current Configuration:**
- No budget limits detected
- No repeat-call detection
- No timeout configuration

**Estimated Monthly Cost (without SHACKLE):** $[estimate]
**Estimated Monthly Cost (with SHACKLE):** $[estimate]
**Potential Savings:** $[difference]

## Recommendations
1. [Specific recommendation]
2. [Specific recommendation]
3. [Specific recommendation]

## Next Steps
Review the attached SHACKLE configuration and integration guide.
Estimated integration time: [15-30 minutes]
```

#### 2. Custom SHACKLE Configuration

Create: `~/clients/[client-name]/deliverables/shackle_config.py`

**Template:**

```python
"""
SHACKLE Configuration for [Client Name]
Generated: [Date]
Framework: [CrewAI/LangGraph/AutoGen]

INSTALLATION:
pip install git+https://github.com/Fame510/SHACKLE-PRO-.git

USAGE:
Replace your existing kickoff/invoke call with the wrapped version below.
"""

from shackle import Guard

# =============================================================================
# CUSTOM CONFIGURATION FOR YOUR AGENT
# =============================================================================

# Global circuit breaker settings
@Guard(
    # Budget limit: Stop execution if token costs exceed this amount
    # Based on your typical workflow: [reasoning for this value]
    budget=0.50,  # $0.50 per run
    
    # Repeat call detection: Trip breaker if same tool called N times
    # Your [tool-name] tool is most vulnerable - catching on 3rd attempt
    max_repeat_calls=3,
    
    # Timeout: Hard stop if execution exceeds this duration
    # Your typical runs take [X] seconds, allowing buffer
    timeout_seconds=180,  # 3 minutes
    
    # Tool-specific overrides (optional)
    tool_overrides={
        '[vulnerable-tool-name]': {
            'max_repeat_calls': 2  # Stricter limit for problem tool
        }
    }
)
def safe_agent_run():
    """
    Your existing agent code, wrapped in SHACKLE protection.
    
    BEFORE (vulnerable):
        result = crew.kickoff()
    
    AFTER (protected):
        result = safe_agent_run()
    """
    
    # REPLACE THIS LINE with your actual agent initialization
    # Example for CrewAI:
    # crew = Crew(agents=[...], tasks=[...])
    # return crew.kickoff()
    
    # Example for LangGraph:
    # graph = StateGraph(...)
    # return graph.invoke(initial_state)
    
    # YOUR CODE HERE:
    pass  # Replace with your actual code


# =============================================================================
# USAGE IN YOUR MAIN FILE
# =============================================================================

if __name__ == "__main__":
    # Simply call the wrapped function instead of your original kickoff
    result = safe_agent_run()
    print(result)


# =============================================================================
# INTERACTIVE HITL CONSOLE
# =============================================================================
# When SHACKLE trips a circuit breaker, you'll see:
#
# ⛓️ SHACKLE CIRCUIT BREAKER: REPETITIVE_TOOL_CALL
# Agent: [YourAgent]
# Tool: [tool-name]
# Input: {...}
# Call Count: 3x
# 
# Options:
#  [R] Resume/Reset — clear history, continue execution
#  [S] Skip — return dummy output, attempt context flush
#  [A] Abort — hard terminate the current run
#
# Select action (R/S/A):

# =============================================================================
# ADJUSTING THRESHOLDS
# =============================================================================
# After testing in your environment, you may want to adjust:
#
# - Increase budget if legitimate runs exceed $0.50
# - Decrease max_repeat_calls if you want faster loop detection
# - Adjust timeout_seconds based on your typical runtime
#
# Test in a non-production environment first!
```

#### 3. Integration Guide

Create: `~/clients/[client-name]/deliverables/Integration-Guide.md`

**Template:**

```markdown
# SHACKLE Integration Guide
**Client:** [Name/Company]  
**Framework:** [CrewAI/LangGraph/AutoGen]  
**Generated:** [Date]

## Prerequisites
- Python 3.10+
- Your existing agent codebase
- 15-30 minutes

## Step 1: Install SHACKLE

```bash
pip install git+https://github.com/Fame510/SHACKLE-PRO-.git
```

## Step 2: Backup Your Code

```bash
git commit -am "Pre-SHACKLE backup" # If using git
# OR
cp -r your-project your-project-backup
```

## Step 3: Add Configuration File

Copy the attached `shackle_config.py` to your project root:

```bash
your-project/
├── shackle_config.py  ← NEW FILE
├── main.py            ← Your existing entry point
└── ...
```

## Step 4: Modify Your Main File

**File to edit:** `[main.py or specific file]`

**Find this code (approximately line [X]):**

```python
# BEFORE - Your vulnerable code
[exact code from their repo]
```

**Replace with:**

```python
# AFTER - SHACKLE protected
from shackle_config import safe_agent_run

result = safe_agent_run()
```

**Full example:**

```python
# BEFORE:
from crewai import Crew, Agent, Task

crew = Crew(agents=[...], tasks=[...])
result = crew.kickoff()  # VULNERABLE

# AFTER:
from shackle_config import safe_agent_run

result = safe_agent_run()  # PROTECTED
```

## Step 5: Test in Non-Production

```bash
python main.py
```

**Expected behavior:**
- Agent runs normally
- If loop detected, SHACKLE pauses and shows HITL console
- You can Resume/Skip/Abort

## Step 6: Verify Circuit Breakers

### Test 1: Budget Limit
Temporarily set budget very low in `shackle_config.py`:
```python
budget=0.01  # Should trip immediately
```

Run your agent. SHACKLE should halt with `BUDGET_EXCEEDED`.

### Test 2: Repeat Call Detection
If you know a tool that might loop, trigger it intentionally.
SHACKLE should catch on the 3rd attempt.

### Test 3: Timeout
Set timeout very low:
```python
timeout_seconds=5  # 5 seconds
```

Run your agent. Should trip if execution exceeds 5 seconds.

## Step 7: Restore Production Settings

Once tested, restore original thresholds in `shackle_config.py`:
```python
budget=0.50
max_repeat_calls=3
timeout_seconds=180
```

## Step 8: Deploy to Production

Commit your changes:
```bash
git add shackle_config.py main.py
git commit -m "Add SHACKLE circuit breaker protection"
git push
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'shackle'"
→ SHACKLE not installed. Run: `pip install git+https://github.com/Fame510/SHACKLE-PRO-.git`

### "SHACKLE keeps tripping on legitimate calls"
→ Budget too low. Increase `budget=` value in `shackle_config.py`

### "Loop not detected fast enough"
→ Decrease `max_repeat_calls=` value (try 2 instead of 3)

### "Agent runs slower after SHACKLE"
→ Minimal overhead (<5%). Check if timeout is too aggressive.

## Support

Questions? Email: docspoc101@gmail.com  
30-day support included (response within 48 business hours)

## Next Steps

1. Test thoroughly in non-production
2. Adjust thresholds based on your testing
3. Monitor first few production runs closely
4. Email if you encounter any issues

Your 30-day support period starts today: [Date]
```

---

## 📋 STAGE 5: DELIVER TO CLIENT

### When All Deliverables Are Ready:

**Send delivery email:**

```
Subject: SHACKLE Implementation - Deliverables Ready

Hi [Name],

Your SHACKLE integration is complete! Attached are your deliverables:

1. **Architecture-Audit.pdf** - Full analysis of your agent code
2. **shackle_config.py** - Your custom configuration (ready to use)
3. **Integration-Guide.md** - Step-by-step instructions

## Quick Start

1. Review the audit report to understand the vulnerabilities we found
2. Install SHACKLE: `pip install git+https://github.com/Fame510/SHACKLE-PRO-.git`
3. Follow the Integration Guide (usually takes 15-30 minutes)
4. Test in non-production environment first
5. Adjust thresholds based on your testing

## Important Notes

- **Test before production deployment**
- The configuration is calibrated to your typical usage patterns
- You can adjust budget/timeout values in shackle_config.py
- Keep your SHACKLE config in version control

## Your 30-Day Support Starts Today

- Support period: [Today's Date] through [Date + 30 days]
- Email: docspoc101@gmail.com
- Response time: Within 48 business hours

Feel free to email with any questions during integration.
If you hit any issues, send me:
- The error message
- What you were trying to do
- Relevant code snippet

I'll help you get it working.

Best,
Dante Bullock
Sovereign Logic
docspoc101@gmail.com
```

**Attachments:**
- Architecture-Audit.pdf
- shackle_config.py
- Integration-Guide.md

---

### Update Records:

```bash
# Mark as delivered
echo "Delivered: $(date)" >> ~/clients/[client-name]/status.txt
echo "Support ends: $(date -d '+30 days')" >> ~/clients/[client-name]/status.txt

# Set reminder for support end date
# (30 days from today)
```

---

## 📋 STAGE 6: 30-DAY SUPPORT

### When Client Emails with Question:

**Response time: Within 48 business hours**

### Support Scope - IN SCOPE:

✅ **Configuration issues:**
```
Client: "SHACKLE keeps tripping even though agent is working fine"
You: [Diagnose - likely budget too low, provide adjusted value]
```

✅ **Integration errors:**
```
Client: "Getting ModuleNotFoundError"
You: [Check installation, provide fix]
```

✅ **SHACKLE-specific bugs:**
```
Client: "Circuit breaker not detecting my loop"
You: [Review their config, adjust max_repeat_calls or tool_overrides]
```

✅ **Threshold adjustments:**
```
Client: "What should I set budget to?"
You: [Review their usage, recommend value]
```

### Support Scope - OUT OF SCOPE:

❌ **Their agent code bugs:**
```
Client: "My agent gives wrong answers"
You: "That's outside SHACKLE's scope. SHACKLE prevents loops and budget overruns, but doesn't affect agent logic. I can help with that as separate consulting at $200/hour if interested."
```

❌ **Feature requests:**
```
Client: "Can you add X feature to SHACKLE?"
You: "I'll add that to the roadmap for a future release, but it's outside the scope of this implementation service."
```

❌ **General consulting:**
```
Client: "How should I restructure my entire agent?"
You: "That's beyond SHACKLE integration. I offer separate architecture consulting at $200/hour if you'd like help with that."
```

### Sample Support Responses:

**Quick fix (in scope):**
```
Subject: Re: SHACKLE Issue - Budget Tripping Too Often

Hi [Name],

Based on your logs, your typical runs cost ~$0.75 in tokens,
but your budget is set to $0.50. That's why it's tripping.

Update shackle_config.py line 24:
budget=1.00  # Increased from 0.50

Test it and let me know if you're still seeing issues.

Best,
Dante
```

**Out of scope (but helpful):**
```
Subject: Re: Agent Architecture Question

Hi [Name],

That's a good question, but it's outside the scope of SHACKLE
integration support. SHACKLE handles loop prevention and budget
enforcement, but agent architecture design is separate consulting.

If you'd like help with that, I offer architecture consulting at
$200/hour. Let me know if you're interested and we can schedule a call.

For your immediate SHACKLE questions, I'm here to help!

Best,
Dante
```

---

## 📋 STAGE 7: SUPPORT PERIOD ENDS

### At 30-Day Mark:

**Send closure email:**

```
Subject: SHACKLE Implementation - Support Period Complete

Hi [Name],

Your 30-day support period ended on [Date].

Hope SHACKLE has been working well for you! If you've
seen cost savings or caught any loops, I'd love to hear about it.

## Ongoing Support Options

If you need continued support or have questions:

- **Ad-hoc:** $200/hour for specific issues
- **Retainer:** $500/month (5 hours included)

Just reply if you'd like to continue.

## Quick Favor

If SHACKLE has been helpful, a GitHub star would mean a lot:
https://github.com/Fame510/SHACKLE-PRO-

Or if you'd be willing to share a brief testimonial,
I'd be happy to feature it (anonymously if you prefer).

Thanks for being an early client!

Best,
Dante Bullock
Sovereign Logic
```

---

### Clean Up:

```bash
# Delete client code (keep deliverables)
rm -rf ~/clients/[client-name]/code/

# Archive correspondence
gzip ~/clients/[client-name]/correspondence/*.eml

# Update status
echo "Status: Complete - $(date)" >> ~/clients/[client-name]/status.txt
```

---

## 🚨 EMERGENCY SITUATIONS

### Client Demands Refund After Delivery:

**If within 7 days AND deficiencies are legitimate:**
- Review their complaint
- If deliverables truly missing promised components: Issue refund
- If they just don't like it: Offer to fix specific issues first

**If after 7 days:**
- Service Agreement states no refunds after 7 days
- Offer extended support instead

### Client Becomes Abusive:

- Remain professional in one response
- If abuse continues: "I'm unable to continue this engagement. Per our Service Agreement Section 11, I'm terminating support. You have the deliverables provided. Best wishes."
- Issue partial refund if fair (your judgment)

### Your Delivery Will Be Late:

**If you realize you'll miss 72-hour deadline:**

Email immediately:
```
Hi [Name],

Quick update: Your audit is taking longer than expected due to
[specific reason - e.g., "complexity of your multi-agent setup"].

New ETA: [Date, within 48 hours]

I'll have everything to you by then. Appreciate your patience.

Best,
Dante
```

---

## ✅ QUALITY CHECKLIST

Before sending deliverables, verify:

- [ ] Audit report is > 2 pages with real findings (not generic)
- [ ] Configuration file has actual values (not placeholders like `YOUR_VALUE_HERE`)
- [ ] Integration guide references their specific files/code
- [ ] All deliverables are professionally formatted (no typos)
- [ ] File names are correct (Architecture-Audit.pdf not audit.pdf)
- [ ] Client's name is correct throughout
- [ ] No references to other clients or projects

---

## 📊 SUCCESS METRICS

**You know it's working when:**
- Client successfully integrates SHACKLE (responds positively)
- Minimal support emails during 30 days
- Client refers another customer
- No refund requests
- Positive testimonial

**Red flags to watch:**
- Client never responds after paying (follow up after 7 days)
- Multiple support emails daily (scope creep or unrealistic expectations)
- Confusion about what was delivered (deliverables unclear)

---

**This process is designed to be repeatable. Follow it for each client and refine as you learn what works.**
