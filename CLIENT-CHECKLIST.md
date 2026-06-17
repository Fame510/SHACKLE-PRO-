# 💰 $2,500 CLIENT CHECKLIST

Quick reference for handling paying clients. Print this or keep it open.

---

## ☑️ WHEN PAYMENT COMES IN

**Within 24 hours:**

- [ ] Note Stripe Transaction ID: ________________
- [ ] Email client with NDA.md attached
- [ ] Email client with SERVICE-AGREEMENT.md attached
- [ ] Use welcome email template (see LEGAL-DOCS-README.md)
- [ ] Create folder: `~/clients/[client-name]/`
- [ ] Wait for signed NDA before they send code

---

## ☑️ WHEN NDA IS SIGNED

**Same day:**

- [ ] Save signed NDA to `~/clients/[client-name]/NDA-signed.pdf`
- [ ] Reply: "NDA received. Please send your code/repo link"
- [ ] Wait for code

---

## ☑️ WHEN CODE ARRIVES

**Immediately:**

- [ ] Save repo URL or code to `~/clients/[client-name]/code/`
- [ ] Forward to AI assistant with this message:
  
  ```
  New SHACKLE client: [Name]
  Repo: [URL or "see attached zip"]
  Framework: [CrewAI/LangGraph/AutoGen/Unknown]
  Issue: [Brief description from client]
  
  Please:
  1. Clone/analyze code
  2. Identify agent initialization points
  3. Audit loop risks and token usage
  4. Create custom SHACKLE config
  5. Write architecture audit report
  6. Write integration guide
  
  Deliverables needed in 48 hours.
  ```

- [ ] Set reminder for 48 hours from now
- [ ] Reply to client: "Code received. Audit in progress. Deliverables in 48-72 hours."

---

## ☑️ WHEN AI COMPLETES ANALYSIS

**Before sending to client:**

- [ ] Review AI's audit report (skim for major issues)
- [ ] Save deliverables to `~/clients/[client-name]/deliverables/`
  - [ ] Architecture-Audit.pdf (or .md)
  - [ ] shackle_config.py
  - [ ] Integration-Guide.md

- [ ] Sanity check:
  - [ ] Config file has actual values (not placeholders)
  - [ ] Integration guide mentions client's specific files
  - [ ] Audit report is > 1 page with real findings

- [ ] Send to client using delivery email template
- [ ] Mark delivery date: ________________
- [ ] Note: 30-day support ends on: ________________

---

## ☑️ DURING 30-DAY SUPPORT

**When client emails with issue:**

- [ ] Forward exact error message + context to AI assistant
- [ ] AI diagnoses and provides fix
- [ ] Send fix to client with clear instructions
- [ ] Mark response time (should be < 48 hours)

**Support INCLUDES:**
- ✅ SHACKLE configuration bugs
- ✅ Integration errors
- ✅ "Why did circuit breaker trip?" questions
- ✅ Adjusting thresholds

**Support DOES NOT include:**
- ❌ Debugging their entire agent code
- ❌ "Build me a new feature"
- ❌ "Rewrite my agent architecture"
- ❌ Questions unrelated to SHACKLE

**If out of scope:**
> "That's outside the scope of SHACKLE support. I can help with that as additional consulting at $200/hour if you're interested."

---

## ☑️ AFTER 30 DAYS

- [ ] Delete client code from your system (keep deliverables)
- [ ] Archive email thread
- [ ] Mark client as "Complete" in tracking

**If client needs more help:**
> "Your 30-day support period ended on [DATE]. I'm happy to continue helping at $200/hour or $500/month retainer (5 hours). Let me know if you'd like to continue."

---

## 🚨 RED FLAGS - ISSUE REFUND

Stop and refund if:
- [ ] Code is not Python
- [ ] Code doesn't use CrewAI/LangGraph/AutoGen
- [ ] Code is incomplete/won't run
- [ ] Code is so poorly documented you can't understand it
- [ ] Client becomes abusive or makes unreasonable demands
- [ ] You can't deliver within 72 hours for reasons outside your control

**Refund process:**
1. Email client: "After reviewing your code, it's not compatible with SHACKLE because [reason]. I'm issuing a full refund."
2. Refund via Stripe dashboard
3. Delete their code immediately
4. No hard feelings

---

## 📊 CLIENT TRACKING

Keep a simple log:

| Client Name | Payment Date | Stripe ID | Code Received | Delivered | Support Ends | Status |
|-------------|--------------|-----------|---------------|-----------|--------------|--------|
| Example Co  | 2026-06-17   | ch_abc123 | 2026-06-18    | 2026-06-20| 2026-07-20   | Active |

---

## 💡 QUICK TIPS

**Stay professional:**
- Always use proper grammar in emails
- Respond within 24-48 hours
- Under-promise, over-deliver

**Protect yourself:**
- Never promise "100% prevention" of loops
- Always test configurations before sending
- Keep records of everything

**Make it easy:**
- Use the email templates (don't freestyle)
- Let AI do the technical work
- You just manage communication

**When in doubt:**
- Ask the client for clarification
- Forward complex questions to AI assistant
- Check the Service Agreement terms

---

## ✅ YOU'RE READY

You have everything you need:
- Clear process
- Legal protection
- AI to do the technical work
- Email templates

**When that $2,500 payment hits, just follow this checklist. You got this.**
