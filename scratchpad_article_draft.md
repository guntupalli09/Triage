# Stop Asking If Legal AI Is Accurate. Start Asking If It's Reproducible.

Run the same contract through the same AI system 20 times. Should a lawyer expect the same legal findings 20 times?

In experiments from my research published at ICCS 2026, the answer for a pure large-language-model pipeline was no. Across identical repeated executions on the same documents, the LLM baseline produced an average of 18.3 distinct output sets out of 20 runs. A deterministic hybrid architecture, evaluated on the same corpus, produced one.

That gap points to a question legal teams should be asking AI vendors far more often than they currently do: **Can your system make the same decision twice?**

## The accuracy question is the wrong first question

Most legal AI marketing — and most legal AI due diligence — still centers on accuracy. How good is the model at spotting risk? How does it compare on benchmark X? These are reasonable questions, but they quietly assume something that shouldn't be assumed: that the system's output is stable enough for "accuracy" to mean anything at all.

If a tool gives you a different risk assessment on Tuesday than it gave you on Monday, for the exact same contract, accuracy becomes a moving target. You can't audit a result you can't reproduce. You can't defend a finding in front of a partner, a regulator, or opposing counsel if the system might have said something else had you clicked "analyze" a second time.

That's not a hypothetical. It's what the experiment measured directly. Beyond the output variance, the two systems were also scored on determinism (whether repeated runs on identical inputs produce identical results) and traceability (whether every output can be linked to a stable identifier and an exact span of the source text). The deterministic hybrid architecture scored 100% on both. The pure LLM baseline scored 0% on both.

## Why this happens

The instinct is to blame the model — a bigger, better, more carefully fine-tuned LLM will fix this eventually. It won't, not fully. Non-determinism isn't a bug in any particular model; it's a structural property of probabilistic text generation. Sampling from a probability distribution, even a very good one, does not guarantee the same output twice. That's true of every general-purpose LLM in production today, and it will remain true as models improve, because it's inherent to how they generate text, not a symptom of how well they're trained.

Which means the fix isn't a smarter model. It's an architectural decision about which parts of a legal AI system are allowed to make decisions at all, and which parts are only allowed to explain decisions someone — or something — else already made.

## Decision engine vs. explanation layer

In the architecture I built and tested for contract risk triage, this separation is treated as a hard boundary, not a best practice. A deterministic rule engine — versioned, auditable, built on explicit pattern logic rather than statistical inference — is solely responsible for identifying risk in a contract. It never guesses. It matches known patterns, applies context rules, and produces findings that are always the same for the same input.

The LLM sits downstream of that engine, not inside it. It never sees the raw contract. It receives only the structured findings the deterministic engine has already produced, and its job is narrow: explain, in plain language, why a given finding might matter. It cannot introduce a risk the deterministic layer didn't flag. It cannot change a severity rating. If the LLM component fails outright, the deterministic findings are still complete and usable — the system degrades safely instead of failing silently.

The result, measured directly rather than assumed, is a system where the parts that must be defensible — what was flagged, and why it was flagged — are fully reproducible and traceable, while the parts that benefit from language fluency — how a finding is explained to a business stakeholder — are handled by the component actually suited to that job.

## Where the market is heading

In a recent conversation, legal community builder and podcast host Robert Hanna made a distinction worth sitting with: as legal AI model performance becomes increasingly commoditized, differentiation will shift toward trust, explainability, and accountability. He also pointed out something more specific — that firms are already asking for this today, just indirectly, through governance requirements, audit demands, and risk controls, even if "reproducibility" isn't yet the word they're using at the negotiating table.

That tracks with what the experiment suggests. The market doesn't need to wait for a high-profile AI failure to start asking the right question. The question is already available, and it's a simple one to put to any vendor: run this analysis twice, and show me it comes back the same.

## The nuance that matters

None of this is an argument that probabilistic AI is bad, or that deterministic systems are simply "better." Probabilistic generation is what makes LLMs genuinely useful — for summarizing, explaining, adapting language to an audience, and handling the linguistic variability that rigid rule systems can't. The point isn't to choose between deterministic and probabilistic AI.

The point is narrower and more defensible: probabilistic generation and authoritative decision-making should not automatically live in the same architectural layer in high-stakes legal workflows. Let the model do what it's good at — explaining. Don't let it do what it's structurally unsuited for — deciding, in a way that has to be reproducible and defensible after the fact.

That's a design choice, not a technology limitation. And it's one legal teams can start evaluating for now, before reproducibility becomes the industry's next headline.

---

*Santhosh Guntupalli is an independent researcher and the builder of TriageCounsel, a contract risk analysis platform. His paper on deterministic execution frameworks for hybrid symbolic-probabilistic pipelines was published at ICCS 2026.*
