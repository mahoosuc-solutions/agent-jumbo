# Module 13: Advanced Knowledge Ops

> **Learning Path:** Knowledge & Content Strategist
> **Audience:** Content managers, knowledge workers, and information architects
> **Prerequisites:** Modules 11–12 — Knowledge System Foundations, Digest & Distribution

---

## Lesson: RAG Quality Optimization

### Why This Matters

Retrieval-Augmented Generation (RAG) is the engine that turns your knowledge base into intelligent answers. When a user asks a question, RAG retrieves the most relevant chunks from your knowledge base and feeds them to the language model, which generates an answer grounded in your actual data.

But "grounded in your data" is only as good as the retrieval quality. If RAG retrieves the wrong chunks, the model produces confident, well-written, completely wrong answers. This is worse than no answer at all, because the user trusts the system.

**The RAG quality equation:**

```text
Answer Quality = Retrieval Quality × Generation Quality
```

If retrieval is 50% accurate, it does not matter how good your language model is. Half the time it is working with the wrong information. Optimizing RAG means obsessing over retrieval quality first.

**What bad RAG looks like in practice:**

| Symptom | Root Cause | User Experience |
|---|---|---|
| Answers are plausible but wrong | Retrieved chunks are from a similar but different topic | "The system told me the wrong policy" |
| Answers are vague and generic | Retrieved chunks lack specifics | "It just says 'follow standard procedure'" |
| Answers contradict each other | Retrieved chunks from different document versions | "It said X yesterday and Y today" |
| Answers miss key details | Chunks are too small, cutting off critical context | "It left out the most important step" |
| No answer found when one exists | Query phrasing does not match document language | "The system says it does not know, but I know we have that doc" |

### How to Think About It

**The Three Levers of RAG Quality**

You can improve RAG by tuning three things:

```text
CHUNK QUALITY ──→ EMBEDDING QUALITY ──→ RETRIEVAL STRATEGY
     |                    |                      |
 Size, overlap,     Model choice,          Search method,
 coherence,         fine-tuning,           re-ranking,
 metadata           dimensionality         filtering
```

**Lever 1: Chunk Quality**

The single biggest factor in RAG quality is how you chunk your documents.

| Chunk Size | Pros | Cons | Best For |
|---|---|---|---|
| Small (100-200 tokens) | Precise retrieval, less noise | Loses context, fragments ideas | FAQ-style knowledge, definitions |
| Medium (300-600 tokens) | Good balance of precision and context | May still split complex topics | SOPs, process docs, guides |
| Large (700-1200 tokens) | Full context preserved | May include irrelevant content | Policies, legal docs, research |

**Tuning approach:**

1. Start with medium chunks (400-500 tokens)
2. Test with 20 representative questions
3. For questions that return fragmented answers, increase chunk size
4. For questions that return noisy answers, decrease chunk size
5. Consider per-document-type chunk sizes rather than one global setting

**Overlap is critical.** When you split a document into chunks, include 50-100 tokens of overlap between adjacent chunks. This prevents the problem where the answer spans a chunk boundary.

```text
Without overlap:
  Chunk 1: "...the cleaning process ends with inspection."
  Chunk 2: "The inspector checks all 15 items on the checklist..."

With 50-token overlap:
  Chunk 1: "...the cleaning process ends with inspection. The inspector checks all 15 items..."
  Chunk 2: "The inspector checks all 15 items on the checklist and signs off..."
```

**Lever 2: Embedding Quality**

Embeddings are the numerical representations of your text chunks. Better embeddings mean better similarity matching between queries and documents.

| Factor | Impact | How to Optimize |
|---|---|---|
| Model choice | High | Use domain-appropriate embedding models; general-purpose models work for most cases |
| Dimensionality | Medium | Higher dimensions capture more nuance but cost more; 768-1536 is the sweet spot |
| Input preprocessing | Medium | Remove boilerplate, normalize formatting before embedding |
| Domain vocabulary | Medium | If your domain has specialized terms, verify the model handles them well |

**Lever 3: Retrieval Strategy**

How you search and rank results matters as much as what you search.

```text
User Query
    |
    ▼
Vector Search (semantic similarity)
    |
    ▼
Metadata Filtering (domain, doc_type, date range)
    |
    ▼
Re-ranking (cross-encoder scoring for precision)
    |
    ▼
Top-K Selection (return best 3-5 chunks)
    |
    ▼
Context Assembly (combine chunks into coherent context)
    |
    ▼
Generation (LLM produces answer from context)
```

### Step-by-Step Approach

**Step 1: Establish a retrieval quality baseline**

Create a test set of 20-30 questions with known correct answers:

```text
{{knowledge_base(action="create_test_set", name="rag-quality-baseline", questions=[{"question": "What is the checkout cleaning procedure for studio units?", "expected_source": "cleaning-checklist-studio.pdf", "expected_answer_contains": ["vacuum", "bathroom", "linens", "inspection"]}, {"question": "What is the guest noise complaint policy?", "expected_source": "guest-policies-2026.md", "expected_answer_contains": ["warning", "quiet hours", "10 PM", "escalation"]}, {"question": "How do I submit a maintenance request?", "expected_source": "maintenance-sop.md", "expected_answer_contains": ["priority level", "photo", "submit form", "response time"]}])}}
```

**Step 2: Run the baseline test**

```text
{{knowledge_base(action="test_retrieval", test_set="rag-quality-baseline", config={"top_k": 5, "chunk_size": 500, "overlap": 50})}}
```

Record baseline metrics:

- **Recall@5:** What percentage of test questions retrieve the correct source document in the top 5 results?
- **Precision@3:** Of the top 3 retrieved chunks, what percentage are actually relevant?
- **Answer accuracy:** When the LLM generates an answer from retrieved chunks, what percentage are correct?

**Step 3: Tune chunk size**

```text
{{knowledge_base(action="test_retrieval", test_set="rag-quality-baseline", config={"top_k": 5, "chunk_size": 300, "overlap": 50})}}
```

```text
{{knowledge_base(action="test_retrieval", test_set="rag-quality-baseline", config={"top_k": 5, "chunk_size": 800, "overlap": 100})}}
```

Compare results across chunk sizes. The best chunk size is the one that maximizes Recall@5 and answer accuracy simultaneously.

**Step 4: Enable re-ranking**

```text
{{knowledge_base(action="configure", setting="retrieval", value={"strategy": "vector_search_with_rerank", "top_k_initial": 20, "rerank_top_k": 5, "rerank_model": "cross-encoder", "metadata_boost": {"freshness_weight": 0.1, "doc_type_match_boost": 0.2}})}}
```

**Step 5: A/B test retrieval configurations**

```text
{{knowledge_base(action="ab_test", test_set="rag-quality-baseline", config_a={"name": "baseline", "chunk_size": 500, "overlap": 50, "rerank": false}, config_b={"name": "optimized", "chunk_size": 400, "overlap": 75, "rerank": true})}}
```

### Practice Exercise

**Scenario:** Your knowledge base has 200 documents and users report that 30% of answers are "not quite right." You need to diagnose and fix the retrieval quality.

**Task:**

1. Create a test set from the 10 most-asked questions (check query logs)
2. Run a baseline test
3. Identify the most common failure mode (wrong doc? fragmented chunk? outdated info?)
4. Apply one fix and re-test

```text
{{knowledge_base(action="query_log", period="last_30_days", sort_by="frequency", limit=10)}}
```

Use the top 10 queries to build your test set, then run the diagnostic:

```text
{{knowledge_base(action="test_retrieval", test_set="top-queries-diagnostic", config={"top_k": 5, "chunk_size": 500, "overlap": 50, "return_debug": true})}}
```

The `return_debug` flag shows you exactly which chunks were retrieved and why. Look for patterns: Are failures clustered around specific document types? Specific topics? Specific query styles?

**Self-check:** After your fix, re-run the test set. Did accuracy improve by at least 10 percentage points? If not, you may be tuning the wrong lever. Check whether the problem is retrieval (wrong chunks) or generation (right chunks, wrong answer). They require different fixes.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Optimizing generation before retrieval | LLM prompt tuning feels more familiar | Fix retrieval first; it accounts for 80% of answer quality |
| One chunk size for all document types | Simplicity | Use per-doc-type chunk sizes: small for FAQs, large for policies |
| No overlap between chunks | Saves storage | Always use 50-100 token overlap; the cost is tiny, the benefit is large |
| No test set | "I'll know good quality when I see it" | Create 20+ test questions with expected answers before tuning anything |
| Tuning once and forgetting | "It works now" | Re-run quality tests monthly and after every major content addition |

---

## Lesson: Brand Voice and Writing Standards

### Why This Matters

Every piece of content your knowledge system produces — digests, answers, summaries, alerts — carries your brand voice. Inconsistent voice undermines trust. If Monday's digest reads like a formal report and Tuesday's reads like a casual text message, recipients lose confidence in the system.

Brand voice is especially critical when AI generates content. Without explicit guidelines, AI models default to a generic, slightly formal, vaguely corporate tone that sounds like nobody in particular. Your knowledge system should sound like your organization.

**The consistency problem:**

| Source | Voice Risk | Example |
|---|---|---|
| AI-generated summary | Generic corporate | "We are pleased to inform you that operations proceeded nominally" |
| Human-written digest | Personal but variable | "Everything went great today!" vs. "Ops were solid" |
| Template-based alert | Robotic | "ALERT: Condition detected. Action required. Reference: #4521" |
| Mixed sources | Jarring shifts | All three styles in the same digest |

**What good brand voice achieves:**

- **Recognition** — recipients know who sent it before looking at the sender
- **Trust** — consistent voice signals a reliable, professional system
- **Clarity** — voice guidelines enforce simplicity and directness
- **Efficiency** — writers (human and AI) do not waste time deciding how to phrase things

### How to Think About It

**The Voice Framework: Four Dimensions**

Define your brand voice along four spectrums:

```text
Formal ◄──────────────────────► Casual
  |                                |
"We observe that..."         "Here's the deal..."

Technical ◄────────────────────► Accessible
  |                                |
"The RAG pipeline's recall..."  "Search accuracy improved..."

Verbose ◄──────────────────────► Concise
  |                                |
"It is worth noting that        "Occupancy up 8%."
the occupancy rate has
increased by 8%..."

Passive ◄──────────────────────► Active
  |                                |
"A decision should be made..."  "Decide by Friday."
```

**Recommended position for operational digests:**

- Slightly casual (professional but not stiff)
- Accessible (no jargon unless audience is technical)
- Very concise (every word earns its place)
- Active voice (clear who does what)

**Voice Guidelines Document**

Your voice guide should answer five questions:

1. **Vocabulary:** What words do we use and avoid? (e.g., "guest" not "customer," "issue" not "problem," "resolve" not "fix")
2. **Sentence structure:** Max sentence length? Active voice required? (e.g., max 20 words, active voice always)
3. **Tone by context:** How does tone shift for alerts vs. summaries vs. reports? (e.g., alerts are direct and urgent; summaries are calm and factual)
4. **Numbers and formatting:** How do we present data? (e.g., always use specific numbers, percentages include one decimal)
5. **Prohibited patterns:** What do we never do? (e.g., never use "please be advised," never start with "I hope this message finds you well")

**Audience-Specific Tone Calibration**

| Audience | Tone | Example |
|---|---|---|
| Executive | Direct, metrics-forward, decision-oriented | "Revenue up 12%. Two decisions needed by Friday." |
| Operations team | Practical, specific, action-oriented | "3 check-ins today. Unit 7B needs AC filter before 2 PM." |
| External client | Professional, reassuring, progress-focused | "Project is on track. Milestone 2 delivered. Next review: April 3." |
| New team member | Supportive, explanatory, step-by-step | "Welcome. Here's your first task: review the cleaning checklist and shadow a team lead." |

### Step-by-Step Approach

**Step 1: Define your voice profile**

```text
{{knowledge_base(action="ingest", source="brand-voice-guide.md", format="markdown", metadata={"domain": "internal", "doc_type": "guide", "audience": "all-staff", "freshness_policy": "365 days"})}}
```

**Step 2: Configure AI generation voice settings**

```text
{{digest_builder(action="configure", setting="voice", value={"tone": "professional-casual", "sentence_max_words": 20, "active_voice": true, "vocabulary_preferences": {"use": ["guest", "team member", "resolve", "property"], "avoid": ["customer", "employee", "fix", "unit"]}, "prohibited_phrases": ["please be advised", "as per our conversation", "I hope this finds you well", "at this point in time", "going forward"], "number_format": {"currency": "$X,XXX.XX", "percentages": "X.X%", "dates": "Mon Mar 20", "times": "2:30 PM ET"}})}}
```

**Step 3: Run a consistency check on existing content**

```text
{{knowledge_base(action="audit", scope="all", report_type="voice_consistency", voice_profile="brand-voice-guide")}}
```

This flags content that deviates from your voice guidelines — overly formal passages, passive voice, jargon, prohibited phrases.

**Step 4: Create before/after examples**

Document specific rewrites so writers (human and AI) see the pattern:

| Before (wrong voice) | After (right voice) | Rule Applied |
|---|---|---|
| "It has come to our attention that the occupancy rate has experienced a decline" | "Occupancy dropped to 72% this week" | Concise, active, specific number |
| "The customer expressed dissatisfaction regarding the cleanliness of the unit" | "Guest flagged cleaning issue in Unit 4B" | Use "guest," be specific, active voice |
| "Please be advised that maintenance will be conducted" | "Maintenance scheduled: Unit 7B AC, tomorrow 10 AM" | Remove filler, add specifics |

### Practice Exercise

**Scenario:** You are establishing brand voice for a property management company's automated communications. The company culture is professional but warm, data-driven, and action-oriented.

**Task:**

1. Define the voice profile across all four dimensions
2. Rewrite three sample messages from generic AI output to brand voice
3. Configure the digest builder with your voice settings

Rewrite this AI-generated digest into your brand voice:

**Before (generic AI output):**
> "Good morning. We would like to inform you that there are currently 3 guest check-ins scheduled for today. Additionally, it has been observed that the occupancy rate stands at 83.3%. A maintenance issue was reported yesterday pertaining to the air conditioning system in one of the units. We recommend that appropriate action be taken at the earliest convenience."

**After (brand voice):**

```text
{{telegram_send(action="send", chat_id="ops-channel", message="calendar TODAY — Thu Mar 20\n\nGuest Ops:\n- 3 check-ins scheduled (first at 1:00 PM ET)\n- Occupancy: 83.3% (10/12 properties)\n\nMaintenance:\n- warning Unit 5A AC not cooling — tech scheduled 9:00 AM\n\nAll other properties: no issues checkmark")}}
```

**Self-check:** Read both versions aloud. The first takes 15 seconds and communicates almost nothing specific. The second takes 8 seconds and gives you everything you need to act. That is the brand voice difference.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Voice guide is too vague ("be professional") | Fear of being too prescriptive | Give specific word choices, sentence length limits, and before/after examples |
| Different voice for every channel | Each channel designed independently | Define one core voice; allow minor channel adaptations (Telegram is terser than email) |
| Not configuring AI voice settings | Assuming defaults are fine | Explicitly set voice parameters in every template and generation config |
| Ignoring voice in alerts | Urgency overrides style | Alerts need voice too — clear, direct, specific, but still on-brand |
| No periodic voice audit | Set once, forget | Review content samples quarterly for voice drift |

---

## Lesson: Knowledge Governance

### Why This Matters

Knowledge systems decay. Without governance, every knowledge base follows the same trajectory: enthusiastic launch, rapid content growth, gradual neglect, and eventual abandonment. Six months after launch, 30% of the content is outdated. A year later, users trust nothing in the system and go back to asking colleagues or searching their email.

Governance is the set of rules and processes that keep your knowledge system healthy over time. It is not glamorous, but it is the difference between a system that compounds in value and one that rots.

**The decay curve without governance:**

```text
Knowledge
Quality
  |
  |████████
  |█████████████
  |█████████████████
  |██████████████████████
  |████████████████████████████
  |  ████████████████████████████████
  |     ████████████████████████████████████
  |         ██████████████████████████████████████
  +──────────────────────────────────────────────→ Time
  Launch    3 months    6 months    12 months
  (high)    (good)      (declining) (unusable)
```

**Governance prevents decay by enforcing:**

| Governance Area | What It Prevents | Mechanism |
|---|---|---|
| Freshness policies | Outdated content served as current | Review schedules with expiry dates |
| Ownership assignment | Nobody maintains orphaned content | Every document has a named owner |
| Quality audits | Low-quality content degrades trust | Periodic accuracy and relevance reviews |
| Archival rules | Clutter obscures useful content | Automatic archival of expired/low-value items |
| Access control | Wrong people see wrong information | Role-based visibility and edit permissions |

### How to Think About It

**The Governance Framework**

Knowledge governance has three pillars: Freshness, Quality, and Accountability.

```text
                  GOVERNANCE
                      |
        ┌─────────────┼─────────────┐
        |             |             |
   FRESHNESS      QUALITY     ACCOUNTABILITY
   "Is it         "Is it       "Who is
   current?"      accurate?"   responsible?"
        |             |             |
   - Review        - Accuracy    - Document owners
     schedules       checks      - Review assignments
   - Expiry        - Relevance   - Escalation paths
     dates           scoring     - Performance metrics
   - Archival      - User
     rules           feedback
```

**Freshness Policies**

Different content types have different shelf lives:

| Content Type | Review Frequency | Expiry Action | Example |
|---|---|---|---|
| SOPs and checklists | Every 90 days | Flag for review, warn on retrieval | Cleaning checklist |
| Policies | Every 180 days | Flag for review, restrict until reviewed | Guest cancellation policy |
| Market research | Every 30 days | Archive, mark as historical | Competitor pricing analysis |
| Training materials | Every 180 days | Flag for review | Onboarding guide |
| Meeting notes | Never review | Auto-archive after 90 days | Weekly standup notes |
| Legal/compliance | Every 365 days (or on regulation change) | Escalate to legal owner | Insurance requirements |

**Quality Dimensions**

Every knowledge item can be scored on four quality dimensions:

| Dimension | Score 1 (Poor) | Score 3 (Adequate) | Score 5 (Excellent) |
|---|---|---|---|
| Accuracy | Contains known errors | Mostly correct, minor gaps | Verified correct, peer-reviewed |
| Completeness | Missing critical information | Covers main points | Comprehensive with edge cases |
| Clarity | Confusing, ambiguous | Understandable with effort | Clear to target audience on first read |
| Actionability | No clear takeaway | Implies what to do | Explicit steps or decisions |

**Ownership Model**

Every document needs exactly one owner. The owner is not necessarily the author — they are the person accountable for keeping it current.

```text
Document Owner Responsibilities:
1. Review on schedule (or delegate and verify)
2. Update when business processes change
3. Respond to user-reported issues within 48 hours
4. Archive when content is no longer needed
5. Hand off ownership when changing roles
```

### Step-by-Step Approach

**Step 1: Assign freshness policies to all content**

```text
{{knowledge_base(action="configure", setting="freshness_policies", value={"rules": [{"doc_type": "sop", "review_interval_days": 90, "expiry_action": "flag_and_warn"}, {"doc_type": "policy", "review_interval_days": 180, "expiry_action": "flag_and_restrict"}, {"doc_type": "report", "review_interval_days": 30, "expiry_action": "archive"}, {"doc_type": "guide", "review_interval_days": 180, "expiry_action": "flag_and_warn"}, {"doc_type": "meeting-notes", "review_interval_days": -1, "auto_archive_days": 90}], "notification": {"channel": "telegram", "chat_id": "knowledge-ops", "advance_warning_days": 7}})}}
```

**Step 2: Assign document owners**

```text
{{knowledge_base(action="assign_owners", assignments=[{"domain": "operations", "owner": "ops-manager@company.com", "backup": "senior-ops@company.com"}, {"domain": "finance", "owner": "finance-lead@company.com", "backup": "cfo@company.com"}, {"domain": "compliance", "owner": "legal@company.com", "backup": "coo@company.com"}, {"domain": "customer-knowledge", "owner": "cx-lead@company.com", "backup": "ops-manager@company.com"}])}}
```

**Step 3: Set up the review workflow**

```text
{{knowledge_base(action="configure", setting="review_workflow", value={"trigger": "freshness_expiry", "steps": [{"action": "notify_owner", "channel": "telegram", "message_template": "clipboard REVIEW DUE: {{doc_title}}\nDomain: {{domain}}\nLast reviewed: {{last_review_date}}\nOwner: {{owner}}\n\nReview and update by {{due_date}} or archive if no longer needed."}, {"action": "escalate_if_overdue", "escalate_after_days": 7, "escalate_to": "backup_owner"}, {"action": "restrict_if_overdue", "restrict_after_days": 14, "restriction": "warn_on_retrieval"}]})}}
```

**Step 4: Schedule quality audits**

```text
{{knowledge_base(action="schedule_audit", config={"frequency": "monthly", "scope": "random_sample", "sample_size": 20, "audit_dimensions": ["accuracy", "completeness", "clarity", "actionability"], "output": {"report_to": "knowledge-ops-channel", "format": "telegram_standard"}})}}
```

**Step 5: Configure archival rules**

```text
{{knowledge_base(action="configure", setting="archival", value={"auto_archive_rules": [{"condition": "not_retrieved_in_days", "days": 180, "action": "flag_for_archive_review"}, {"condition": "freshness_expired_and_unreviewd", "days": 30, "action": "archive_with_warning"}, {"condition": "doc_type", "type": "meeting-notes", "age_days": 90, "action": "auto_archive"}], "archive_behavior": {"searchable": true, "retrieval_warning": "This document is archived and may be outdated.", "restore_allowed": true}})}}
```

### Practice Exercise

**Scenario:** You inherited a knowledge base with 500 documents. Nobody has maintained it in 8 months. Users have reported multiple instances of outdated procedures being followed because the knowledge base said to.

**Task:**

1. Run a freshness audit to quantify the problem
2. Identify the 20 most critical documents that need immediate review
3. Set up governance to prevent this from happening again

```text
{{knowledge_base(action="audit", scope="all", report_type="freshness", thresholds={"stale_after_days": 90, "critical_after_days": 180})}}
```

```text
{{knowledge_base(action="query", question="Which documents have been retrieved most in the last 30 days but not reviewed in over 180 days?", filters={"sort_by": "retrieval_count_desc", "limit": 20})}}
```

These 20 documents are your highest-risk items: frequently used but potentially outdated. They are your first review sprint.

**Self-check:** After setting up governance, verify by answering: Can you name the owner of every knowledge domain? Does every document have a freshness policy? Is there an automated alert for overdue reviews? If any answer is no, your governance has a gap.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| No document owners | "Everyone is responsible" | Assign one owner per document or domain; shared ownership means no ownership |
| Review intervals too short | Overcorrecting for past neglect | Match intervals to content volatility; SOPs every 90 days, not every 7 |
| No escalation path | Assumes owners always comply | Automated escalation to backup owner after 7 days overdue |
| Archiving equals deleting | Storage seems cheap | Archive keeps content searchable with a staleness warning; never hard-delete |
| Governance without tooling | Relies on human memory | Automate freshness checks, review notifications, and archival — humans forget |
