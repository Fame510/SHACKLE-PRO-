# Legal Documents for SHACKLE Service

This folder contains the legal documents for the $2,500 SHACKLE Implementation Service.

## 📄 Documents Included

### 1. **NDA.md** (Mutual Non-Disclosure Agreement)
**When to use:** Send this to clients BEFORE they share their code with you.

**Key points:**
- Protects both your IP and their code
- Explicitly covers AI processing (important!)
- 2-year term, 3-year confidentiality survival
- California law

**How to use:**
1. Client pays via Stripe
2. Email them the NDA.md
3. Have them fill in their details and sign (electronic signature is fine)
4. They return it to you
5. You sign and return a copy
6. THEN they send you their code

### 2. **SERVICE-AGREEMENT.md** (Service Contract)
**When to use:** Automatically accepted when client pays via Stripe.

**Key points:**
- $2,500 one-time payment
- 48-72 hour delivery timeline
- 30-day support included
- Clear refund policy
- Limits your liability to $2,500 max
- Client keeps their code rights

**How to use:**
1. Client pays via Stripe (this = acceptance of terms)
2. Email them a copy of SERVICE-AGREEMENT.md within 24 hours
3. No signature needed (payment = agreement)
4. Keep a copy with their Stripe transaction ID

### 3. **index-updated.html** (New Landing Page)
**What changed:**
- Clearer description of what $2,500 gets them
- Step-by-step process section
- FAQ section
- Links to NDA and Service Agreement
- Better description of deliverables

**How to use:**
1. Replace your current `index.html` with this file
2. Rename it to `index.html`
3. Push to GitHub
4. GitHub Pages will update automatically

---

## 🚀 Client Onboarding Workflow

### **Step 1: Client Pays**
- They click Stripe link: https://buy.stripe.com/6oU28q54DbsXdpV6Hy9sk00
- Payment goes through
- You receive notification

### **Step 2: Send Documents (Within 24 hours)**
Email template:
```
Subject: SHACKLE Implementation - Next Steps

Hi [Name],

Thanks for your payment! Here's what happens next:

1. CONFIDENTIALITY
Please review and sign the attached NDA (NDA.md).
This protects both your code and my integration process.

2. SERVICE AGREEMENT
Attached is your Service Agreement (your payment confirms acceptance).
Keep this for your records.

3. SEND YOUR CODE
Once the NDA is signed, reply with:
- GitHub repo URL (preferred) OR zip file of code
- Brief description of your agent's purpose
- Any known cost/loop issues

4. DELIVERY TIMELINE
You'll receive:
- Architecture audit report
- Custom SHACKLE configuration
- Integration guide

Within 48-72 hours of receiving your code.

5. SUPPORT
30 days of email support starts from delivery date.

Questions? Just reply to this email.

Best,
Dante Bullock
Sovereign Logic
docspoc101@gmail.com
```

### **Step 3: Client Sends Code**
- They reply with repo URL or zip file
- You forward it to your AI assistant (me!)
- I do the analysis and create deliverables

### **Step 4: Deliver Results**
Email template:
```
Subject: SHACKLE Implementation - Deliverables Ready

Hi [Name],

Your SHACKLE integration is ready! Attached:

1. Architecture-Audit.pdf - Full review of your agent code
2. shackle_config.py - Your custom configuration
3. Integration-Guide.md - Step-by-step instructions

NEXT STEPS:
1. Review the audit report
2. Follow the integration guide (usually < 30 minutes)
3. Test SHACKLE in a non-production environment first
4. Email me if you hit any issues (30-day support starts now)

IMPORTANT:
- Test before deploying to production
- Adjust budget/timeout values based on your testing
- Keep your SHACKLE config in version control

Your 30-day support period starts today ([DATE]).

Best,
Dante
```

### **Step 5: 30-Day Support**
- Client emails with questions/issues
- You forward to your AI assistant (me)
- I diagnose and provide fix
- You send response to client

---

## ⚖️ Legal Notes

### **California Law**
Both documents use California law because:
- You're based in Oakland, CA
- Provides strong IP protections
- Predictable arbitration rules

### **Liability Limits**
Maximum liability is capped at $2,500 (the service fee) for:
- Protection against massive API bill claims
- Reasonable given the service scope
- Standard for software services

### **What You're NOT Promising**
Service Agreement clearly states you're NOT:
- Guaranteeing 100% loop prevention (LLMs are non-deterministic)
- Debugging their entire codebase
- Liable for their API costs
- Providing unlimited support

### **What You ARE Promising**
- Professional audit within 72 hours
- Custom working configuration
- Clear integration instructions
- 30 days of reasonable support

---

## 📋 Record Keeping

For each client, keep:
1. **Stripe Transaction ID**
2. **Signed NDA** (PDF or email confirmation)
3. **Copy of Service Agreement** (auto-accepted via payment)
4. **Their code/repo link** (delete after 30 days + delivery)
5. **Deliverables you sent them**
6. **Support email thread**

Store in: `~/clients/[client-name]/` folder

---

## 🔒 Security Notes

### **Code Handling**
- Client code is confidential (covered by NDA)
- Delete their code after service completion + 30 days
- Don't share their code with anyone
- AI processing is covered in NDA Section 4

### **NDA Explicitly Covers AI**
Section 4 states:
> "Client acknowledges that Sovereign Logic may use AI Systems to perform services."

This protects you legally for using AI assistants.

---

## ❓ Common Client Questions

**Q: "Do I have to sign the NDA?"**
A: Yes, before you send code. Protects both parties.

**Q: "Can I see examples of past audits?"**
A: No, all client work is confidential. But I can describe the general process.

**Q: "What if my code is a mess?"**
A: If it's truly unworkable, you get a full refund within 5 days.

**Q: "Can I pay in installments?"**
A: No, it's a one-time $2,500 payment upfront.

**Q: "What if I need help after 30 days?"**
A: Extended support available at $200/hour or $500/month retainer.

---

## 🚨 Red Flags (When to Refund)

Issue a refund if:
- Code is not Python
- Code doesn't use any supported frameworks
- Code is incomplete/won't run
- Client becomes abusive or unreasonable
- You can't deliver within reasonable time

**Always refund within 5 business days of identifying incompatibility.**

---

## ✅ You're Ready

You now have:
- ✅ NDA to protect both parties
- ✅ Service Agreement that limits liability
- ✅ Updated landing page with clear terms
- ✅ Client onboarding workflow
- ✅ Email templates

**When someone pays $2,500, you know exactly what to do.**
