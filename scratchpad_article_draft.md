# Stop Asking If Legal AI Is Accurate. Start Asking If It's Reproducible.

Quick question before you trust any legal AI demo: run the same contract through the same system 20 times. Should a lawyer expect the same findings 20 times?

In experiments from my research published at ICCS 2026, the answer for a pure large-language-model pipeline was no. Across identical repeated executions on the same documents, the LLM baseline produced an average of 18.3 distinct output sets out of 20 runs. A deterministic hybrid architecture, evaluated on the same corpus, produced one.

That gap points to a question legal teams should be asking AI vendors far more often than they currently do: **Can your system make the same decision twice?**

I've spent the last two years building and testing that question directly — first as a research problem, then as TriageCounsel, a contract risk platform designed around the answer.

## The accuracy question is the wrong first question

Most legal AI marketing — and most legal AI due diligence — still centers on accuracy. How good is the model at spotting risk? How does it compare on benchmark X? These are reasonable questions, but they quietly assume something that shouldn't be assumed: that the system's output is stable enough for "accuracy" to mean anything at all.

If a tool gives you a different risk assessment on Tuesday than it gave you on Monday, for the exact same contract, accuracy becomes a moving target. You can't audit a result you can't reproduce. You can't defend a finding in front of a partner, a regulator, or opposing counsel if the system might have said something else had you clicked "analyze" a second time.

That's not a hypothetical. It's what the experiment measured directly. Beyond the output variance, the two systems were also scored on determinism (whether repeated runs on identical inputs produce identical results) and traceability (whether every output can be linked to a stable identifier and an exact span of the source text). In this experimental setup, the deterministic hybrid architecture scored 100% on both metrics, while the pure LLM baseline scored 0%.

## Why this happens

The instinct is to blame the model — a smarter, better-tuned LLM will eventually fix this. Only partly true. Fixed seeds and structured output schemas can reduce variance, but as an architectural default, LLM-based decision pipelines generally don't provide reproducibility as a guarantee the way a versioned, rule-based system can. It has to be engineered in — deliberately, at the architecture level, not hoped for from a better model.

Which means the fix is less about a smarter model, and more about deciding which parts of a legal AI system are allowed to make decisions at all — and which parts are only allowed to explain decisions someone, or something, else already made.

## Decision engine vs. explanation layer

In that architecture, the separation is a hard boundary, not a best practice. A deterministic rule engine — versioned, auditable, built on explicit pattern logic rather than statistical inference — is solely responsible for identifying risk in a contract. It matches known patterns, applies context rules, and produces findings that are always the same for the same input.

Determinism does not guarantee that a rule is correct. It guarantees something different: that the same rule applied to the same evidence produces the same result, making errors inspectable, reproducible, and correctable. A deterministic system can still encode an imperfect rule, or miss a clause it was never taught to recognize. What it cannot do is give you a different answer to the same question on a different day. That distinction — consistency, not correctness — is the actual guarantee on offer, and it's a more honest one than most vendors make.

The LLM sits downstream of that engine, not inside it. It never sees the raw contract. It receives only the structured findings the deterministic engine has already produced, and its job is narrow: explain, in plain language, why a given finding might matter. It cannot introduce a risk the deterministic layer didn't flag. It cannot change a severity rating. If the LLM component fails outright, the deterministic findings are still complete and usable — the system degrades safely instead of failing silently.

The result, measured directly rather than assumed, is a system where the parts that must be defensible — what was flagged, and why it was flagged — are fully reproducible and traceable, while the parts that benefit from language fluency — how a finding is explained to a business stakeholder — are handled by the component actually suited to that job.

## Where the market is heading

In conversations across the legal technology community, I keep hearing a related distinction: firms may not explicitly ask vendors for "reproducibility," but they are increasingly asking for the properties around it — governance, auditability, risk controls, and accountability. As model performance becomes increasingly commoditized across vendors, those properties are what's left to differentiate on.

That tracks with what the experiment suggests. The market doesn't need to wait for a high-profile AI failure to start asking the right question. The question is already available, and it's a simple one to put to any vendor: run this analysis twice, and show me it comes back the same.

Here are five worth asking before adopting a legal AI system:

1. If we submit the same document twice, will the substantive findings remain the same?
2. Can every finding be traced to the source language and the logic that produced it?
3. What part of the workflow is controlled by an LLM?
4. Can the model add, remove, or change substantive legal findings?
5. What happens when the model fails or is unavailable?

Question four is the one most vendors will be least comfortable answering. That's exactly why it's worth asking.

## The nuance that matters

None of this is an argument that probabilistic AI is bad, or that deterministic systems are simply "better." Probabilistic generation is what makes LLMs genuinely useful — for summarizing, explaining, adapting language to an audience, and handling the linguistic variability that rigid rule systems can't. The point isn't to choose between deterministic and probabilistic AI.

The point is narrower and more defensible: probabilistic generation and authoritative decision-making should not automatically live in the same architectural layer in high-stakes legal workflows. Let the model do what it's good at — explaining. Don't let it do what it's structurally unsuited for — deciding, in a way that has to be reproducible and defensible after the fact.

That's a design choice, not a technology limitation.

Model performance may win the demo. Practical value may win the pilot. But in legal work, systems eventually have to survive a harder test: can you show exactly how the decision was made — and make the same decision again?

---

*Santhosh Guntupalli is an independent researcher and the founder of TriageCounsel, a contract risk analysis platform. His paper, "Deterministic Execution Frameworks for Hybrid Symbolic–Probabilistic Computational Pipelines," was published at ICCS 2026. [Link to paper, if permitted.]*
