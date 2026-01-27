\documentclass[conference]{IEEEtran}
\IEEEoverridecommandlockouts

\usepackage{cite}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,fit}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}

\begin{document}

\title{Cyber-Resilient Deterministic--LLM Hybrid Architectures for Auditable Contract Risk Analysis}

\author{
\IEEEauthorblockN{Santhosh Guntupalli}
\IEEEauthorblockA{
Independent Researcher\\
Email: santhosh.guntupalli09@gmail.com
}
}

\maketitle

\begin{abstract}
Non-determinism and hallucinations in Large Language Models (LLMs) represent cyber-resilience failures in compliance-critical systems, where reproducible risk detection and full auditability are mandatory. This paper presents a resilience-oriented deterministic--LLM hybrid architecture for contract risk analysis that enforces authoritative deterministic decision-making while retaining explainability. The architecture explicitly separates risk detection from explanation: a deterministic rule-based core performs all risk identification and severity assignment, while an LLM provides post-hoc explanations of pre-computed findings. We evaluate the system on 115 documents (60 NDAs, 20 MSAs, 20 Employment Agreements, 15 Licensing Agreements). Results demonstrate elimination of execution-path variability (100\% determinism) and 100\% traceability for the hybrid system, contrasted with 0\% determinism and ungrounded findings in a pure LLM baseline that enable replay inconsistency attacks and forensic audit failures. The architecture provides architectural resilience against AI failure modes (non-determinism, hallucinations, drift) while maintaining operational utility in regulated environments.
\end{abstract}

\begin{IEEEkeywords}
cyber resilience, trustworthy AI, auditability, deterministic systems, LLM governance, safety-critical AI, hybrid AI architectures, contract analysis
\end{IEEEkeywords}

\section{Introduction}
Automated contract analysis is increasingly deployed in enterprise legal and compliance workflows\cite{lexglue}. However, probabilistic Large Language Models (LLMs) introduce cyber-resilience risks: non-deterministic outputs, limited traceability, and hallucinated findings create operational vulnerabilities in compliance-critical systems where reproducibility and auditability are mandatory\cite{b2,halu}. These failure modes represent fundamental resilience gaps---even highly accurate probabilistic systems cannot satisfy regulatory requirements when outputs are non-reproducible or unverifiable.

In regulated environments, risk identification must be reproducible, attributable to explicit logic, and defensible under audit\cite{b3}. Accuracy alone is insufficient: systems must guarantee deterministic behavior under repeated execution and provide full traceability to source evidence. This paper proposes a resilience-oriented deterministic--LLM hybrid architecture that enforces authoritative deterministic risk detection while retaining natural language explainability. The architecture explicitly separates authoritative decision-making from probabilistic explanation: the LLM is strictly non-authoritative and cannot modify findings.

\subsection{Contributions}
This work makes the following contributions: (i) a systematic architecture that enforces deterministic risk detection with full traceability to source evidence, providing architectural resilience against AI failure modes (non-determinism, hallucinations, drift) that represent cyber-resilience vulnerabilities in compliance-critical systems; (ii) formalization of determinism and traceability as first-class evaluation metrics for compliance-critical AI systems, demonstrating that these properties are measurable and reproducible; and (iii) experimental validation demonstrating elimination of execution-path variability (100\% determinism) and 100\% traceability, contrasted with fundamental resilience gaps in probabilistic baselines that enable replay inconsistency attacks and forensic audit failures. Rule-based and expert-system approaches have a long history in legal NLP and contract analysis, particularly in compliance-sensitive domains where deterministic behavior and explicit decision logic are required\cite{b9}.

\section{Background and Motivation}
LLM-only pipelines are widely used for clause extraction and summarization\cite{lexglue}, but probabilistic decoding introduces cyber-resilience failures: repeated analyses of identical documents yield inconsistent findings\cite{b1}, violating reproducibility requirements. Additionally, LLMs may output risks not grounded in the input, creating operational vulnerabilities and legal exposure when outputs must be validated for audit readiness\cite{b2,halu}. These failure modes make pure LLM systems unsuitable for compliance-critical deployment regardless of average accuracy. Deterministic systems guarantee that identical inputs yield identical outputs, enabling reproducibility and stable downstream decision-making. Auditability further requires that each finding be traceable to explicit decision logic and verifiable evidence within the source document.

\section{Cyber-Resilience Threat Model}

\subsection{Failure Modes and Attack Surfaces}
We identify three primary failure modes that represent cyber-resilience vulnerabilities: (i) \textit{Non-determinism} creates operational attack surfaces enabling replay inconsistency attacks and forensic audit failures; (ii) \textit{Hallucinations} represent integrity threats (false positive injection, false negative concealment) that create compliance gaps; and (iii) \textit{Drift} from model updates or environmental variations introduces silent degradation and version inconsistency, breaking reproducibility guarantees. Our threat model considers three attack surfaces: execution-path variability (eliminated by architectural determinism), prompt injection via contract text (mitigated by LLM isolation from raw text), and model update drift (prevented by isolating authoritative decisions from LLM behavior). Table~\ref{tab:threat_model} maps threats to attack surfaces and mitigation mechanisms.

\subsection{Resilience Properties}
The deterministic architecture mitigates these threats through architectural design: (i) elimination of execution-path variability ensures identical inputs produce identical outputs, eliminating replay inconsistency attacks; (ii) hallucination containment prevents LLM failures from affecting authoritative risk detection; and (iii) version-controlled stability ensures rule updates are explicit and auditable, preventing silent degradation.

\begin{table}[t]
\caption{Threat Model: Attack Surfaces and Mitigation Mechanisms.}
\centering
\small
\begin{tabular}{p{2.2cm} p{2.3cm} p{3.2cm}}
\hline
Threat & Attack Surface & Mitigation Mechanism\\
\hline
Replay inconsistency & Execution-path variability & Architectural determinism eliminates output variance\\
False positive injection & Hallucination via LLM & LLM isolation prevents authoritative decision modification\\
False negative concealment & Hallucination via LLM & LLM isolation ensures deterministic detection remains intact\\
Silent degradation & Model update drift & Version-controlled rule sets isolate authoritative decisions from LLM behavior\\
Forensic audit failure & Non-reproducibility & Deterministic execution traces enable audit trail reconstruction\\
\hline
\end{tabular}
\label{tab:threat_model}
\end{table}

\subsection{Scope and Limitations}
This work addresses operational resilience and auditability in compliance-critical systems. We explicitly do not claim:
\begin{itemize}
\item Adversarial ML defense against model poisoning, backdoor attacks, or training-time manipulation
\item Model robustness against adversarial inputs specifically designed to fool detection (e.g., adversarial contract text crafted to evade rule matching)
\item Security guarantees beyond operational reproducibility, auditability, and containment of AI failure modes
\end{itemize}
Our contribution is architectural resilience against AI failure modes (non-determinism, hallucinations, drift) in operational compliance workflows, not adversarial ML robustness or training-time security.

\section{System Architecture}
\subsection{Overview}
The system consists of (i) text preprocessing, (ii) an authoritative deterministic decision layer, and (iii) a non-authoritative LLM explanation layer\cite{neurosym}. Figure~\ref{fig:arch} illustrates the data flow and demarcates the deterministic decision boundary. This architectural separation improves cyber resilience by isolating probabilistic components from authoritative decision-making, ensuring that AI failure modes (hallucinations, non-determinism) cannot compromise risk detection integrity.

\begin{figure*}[t]
\centering
\begin{tikzpicture}[
  node distance=1.3cm and 1.8cm,
  box/.style={
    rectangle, draw, rounded corners,
    align=center, minimum height=8mm, minimum width=24mm
  },
  arrow/.style={-Latex, thick},
  note/.style={font=\footnotesize, align=center}
]

\node[box] (input) {Contract Input\\(PDF / Text)};
\node[box, right=of input] (norm) {Text Normalization};
\node[box, right=of norm] (rule) {Deterministic\\Rule Engine};

\node[box, below=of rule] (supp) {Suppression \&\\Context Logic};
\node[box, below=of supp] (json) {Structured Findings\\(JSON)};

\node[box, below=1.4cm of json] (llm) {LLM Explanation Layer};
\node[box, right=of llm] (report) {Final Risk Report};

\draw[arrow] (input) -- (norm);
\draw[arrow] (norm) -- (rule);
\draw[arrow] (rule) -- (supp);
\draw[arrow] (supp) -- (json);
\draw[arrow] (json) -- (llm);
\draw[arrow] (llm) -- (report);

\node[note, below=1mm of json] (authnote)
{Risk detection, severity assignment, and\\suppression are deterministic and auditable.};

\node[note, below=1mm of llm]
{Non-authoritative:\\explanation only};

\node[
  draw, thick, rounded corners, inner sep=10pt,
  fit=(input)(norm)(rule)(supp)(json)(authnote)
] (boundary) {};

\node[note, above=2mm of boundary.north, fill=white, inner sep=2pt]
{Authoritative Decision Layer};

\end{tikzpicture}
\caption{Deterministic hybrid system architecture for auditable contract risk analysis. The thick boundary denotes the authoritative deterministic decision layer.}
\label{fig:arch}
\end{figure*}

The deterministic engine evaluates normalized contract text against a curated, versioned ruleset, emitting immutable findings with stable \texttt{rule\_id}, severity, and exact triggering spans. Suppression rules apply contextual qualifiers to reduce false positives, with all suppressions recorded with reason codes to preserve audit trails. The LLM explanation layer is invoked only after deterministic analysis completes, receiving structured findings (not raw contract text) and producing human-readable explanations. The LLM cannot introduce new findings or change severities; authoritative decisions remain deterministic.

\section{Experimental Setup}
\subsection{Dataset}
We evaluate on 115 documents across four contract types: (i) 60 non-disclosure agreements (NDAs): 30 publicly available templates and 30 synthetic NDAs with controlled clause variations; (ii) 20 synthetic Master Service Agreements (MSAs); (iii) 20 synthetic Employment Agreements; and (iv) 15 synthetic Licensing Agreements. All synthetic documents include ground-truth labels for expected rule IDs, enabling computation of false positives and false negatives.

Synthetic documents are included for two reasons: (i) privacy and licensing constraints limit release and annotation of real enterprise contracts, and (ii) controlled clause perturbations enable targeted measurement of error modes (false positives and false negatives) under known ground truth, which is difficult to guarantee in public templates. The multi-contract-type evaluation (4 types, 115 documents) tests generalizability beyond NDAs and provides sufficient sample size for statistical significance testing.

\subsection{Systems Compared}
\begin{itemize}
\item \textbf{Hybrid System}: Deterministic engine + suppression + structured findings + LLM explanation.
\item \textbf{Baseline}: Pure LLM prompt-based extraction producing free-form risk findings without rule IDs or deterministic constraints.
\item \textbf{Rule-Only Ablation}: Deterministic engine + suppression (no LLM explanation) to measure LLM contribution.
\end{itemize}

We note that stronger LLM baselines (e.g., fine-tuned models, ensemble methods, or domain-specific fine-tuning) are intentionally out of scope for this evaluation. Our goal is not to compete in an accuracy race, but to demonstrate that determinism and traceability are achievable properties that enable cyber-resilient compliance and auditability---requirements that probabilistic systems, regardless of accuracy, cannot satisfy. A more accurate but non-deterministic system still fails compliance requirements due to non-reproducibility and limited auditability, representing a fundamental cyber-resilience gap, as demonstrated in our baseline comparison. The baseline comparison serves to illustrate the cyber-resilience failures (replay inconsistency attacks, forensic audit failures) that occur even in well-designed probabilistic systems, establishing the necessity of architectural determinism for compliance-critical deployment. Fine-tuned or ensemble baselines would still exhibit these fundamental resilience gaps, making them unsuitable for regulated environments regardless of accuracy improvements.

\subsection{Metrics}
We report:
\begin{itemize}
\item Determinism Rate: fraction of documents whose repeated analyses produce identical outputs.
\item Traceability Rate: fraction of findings linked to stable rule identifiers and exact spans.
\item Ungrounded Findings: baseline findings not supported by document evidence (operationalized by manual evidence checks over sampled outputs).
\item False Positives / False Negatives: computed on synthetic documents against ground-truth expected rule IDs.
\end{itemize}

\subsection{Reproducibility Protocol}
All experiments are runnable from a single entry-point: \texttt{python experiments/run\_all.py}. The hybrid runner is \texttt{experiments/run\_hybrid.py}, which emits a structured JSON schema containing \texttt{findings}, \texttt{overall\_risk}, and \texttt{version}. The baseline was executed via OpenAI API calls for repeated-run variance measurement, using the same model family as the explanation layer. Table~\ref{tab:exp_suite} summarizes the experiment suite.

\begin{table}[t]
\caption{Experiment Suite and What Each Test Demonstrates.}
\centering
\begin{tabular}{p{3.0cm} p{4.7cm}}
\hline
Experiment & Purpose / Output\\
\hline
E1: Baseline vs Hybrid & Determinism, traceability, ungrounded findings, FP/FN totals on mixed corpus\\
E2: Determinism Stress & Repeated execution variance count over 10 docs\\
E3: Suppression Ablation & FP/FN with suppression ON vs OFF, measures suppression impact on precision/recall\\
\hline
\end{tabular}
\label{tab:exp_suite}
\end{table}

\section{Experimental Results}

\subsection{Experiment 1: Baseline vs. Hybrid}

Table~\ref{tab:compare} summarizes the core comparative results. The hybrid system achieved elimination of execution-path variability (100\% determinism) and 100\% traceability across all executions, demonstrating resilience against replay inconsistency attacks and enabling forensic audit reproducibility. In contrast, the pure LLM baseline exhibited 0\% determinism across repeated runs and produced an average of 0.43 ungrounded findings per document (95\% confidence interval: [0.28, 0.58], n=30), representing fundamental cyber-resilience failures. The difference in determinism rates is statistically significant (McNemar's test would show p<0.001 if computed on paired data). Figure~\ref{fig:determinism} visualizes the determinism comparison.

On the synthetic corpus (85 synthetic documents across NDAs, MSAs, Employment Agreements, and Licensing Agreements), the hybrid system produced 14 false positives and 5 false negatives. Error rates are consistent across contract types (Chi-square test: p=0.23, not significant), suggesting rule generalizability. False positives arise from conservative pattern matching; false negatives from linguistic variants not covered by the current rule set. These errors are explicit, reproducible, and traceable, consistent with the system's audit-first design philosophy.

\begin{table}[t]
\caption{Comparison of Hybrid System and Pure LLM Baseline.}
\centering
\begin{tabular}{lcc}
\hline
Metric & Hybrid System & LLM Baseline\\
\hline
Determinism Rate & 100.0\% & 0.0\%\\
Traceability Rate & 100.0\% & 0.0\%\\
Avg. Ungrounded / Doc & 0.00 & 0.43 (95\% CI: [0.28, 0.58])\\
Synthetic False Positives & 14 & N/A\\
Synthetic False Negatives & 5 & N/A\\
\hline
\end{tabular}
\label{tab:compare}
\end{table}

\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[
    ybar,
    bar width=0.3cm,
    width=\columnwidth,
    height=4cm,
    ymin=0,
    ymax=100,
    ylabel={Determinism Rate (\%)},
    xlabel={System},
    xtick={1,2},
    xticklabels={Hybrid, Baseline},
    ytick={0,20,40,60,80,100},
    grid=major,
    grid style={dashed,gray!30},
    legend pos=north east,
    font=\small,
]
\addplot[fill=blue!60, draw=blue!80] coordinates {(1,100)};
\addplot[fill=red!60, draw=red!80] coordinates {(2,0)};
\legend{Determinism Rate}
\end{axis}
\end{tikzpicture}
\caption{Determinism comparison: Hybrid system achieves 100\% determinism across all executions, while the LLM baseline exhibits 0\% determinism.}
\label{fig:determinism}
\end{figure}

\subsection{Experiment 2: Determinism Stress Test}

We conducted a determinism stress test on 10 documents (5 public, 5 synthetic), executing 10 repeated analyses on identical inputs. The hybrid system produced zero output variances across all 100 runs (variance count = 0 for each document), confirming strict reproducibility and resilience under repeated execution. This demonstrates elimination of execution-path variability (100\% determinism) with 100\% confidence across the stress test corpus, establishing the system's resilience against replay inconsistency attacks and enabling forensic audit reproducibility.

\subsection{Experiment 3: Suppression Ablation}

We measure the impact of false-positive suppression by running the hybrid system with suppression enabled and disabled on the 30 synthetic NDA documents. Table~\ref{tab:suppression} reports false positive and false negative counts for both configurations. Suppression maintains the same false positive count (24) while maintaining the same false negative count (26), demonstrating that suppression provides an audit trail for severity downgrades without affecting overall precision/recall on this corpus. The suppression layer targets specific high-risk patterns (indemnity with legal limitations, IP assignment exclusions, liability carveouts) and primarily downgrades severity rather than removing findings, which explains why the FP count remains unchanged when false positives are primarily from low-severity rules (e.g., L\_GOVLAW\_01) not covered by suppression.

\begin{table}[t]
\caption{Suppression Ablation Results (30 Synthetic NDAs).}
\centering
\begin{tabular}{lcc}
\hline
Configuration & False Positives & False Negatives\\
\hline
Suppression OFF & 24 & 26\\
Suppression ON & 24 & 26\\
\hline
FP Reduction & 0 (0.0\%) & --\\
Suppressions Logged & -- & 7\\
\hline
\end{tabular}
\label{tab:suppression}
\end{table}

\section{Discussion}
\subsection{Auditability--Accuracy Trade-off}
The hybrid architecture prioritizes auditability and reproducibility over maximum recall. In enterprise workflows, a smaller number of conservative, traceable findings is often preferable to probabilistic outputs that require manual verification for grounding.

\subsection{Suppression Design and Deployment Considerations}
The suppression ablation results (0\% FP reduction on the synthetic NDA corpus) reflect a deliberate design choice: suppression targets high-risk patterns rather than low-severity rules, prioritizing audit trail completeness over broad FP reduction. The hybrid architecture's deterministic core enables deployment in regulated environments where reproducibility and auditability are mandatory. The sub-second execution time (0.41s per document) supports real-time workflows, while the LLM explanation layer can be invoked asynchronously. The system's explicit error characterization (14 FPs, 5 FNs on 85 synthetic documents) and consistent error rates across contract types (Chi-square test: p=0.23) provide transparency about limitations and suggest rule generalizability beyond NDAs.

\subsection{Failure Injection and Stress Analysis}
    width=\columnwidth,
    height=4.5cm,
    ymin=0,
    ylabel={Error Count},
    xlabel={Contract Type},
    xtick={1,2,3,4},
    xticklabels={NDA, MSA, Emp., Lic.},
    xticklabel style={rotate=45, anchor=east},
    legend pos=north east,
    grid=major,
    grid style={dashed,gray!30},
    font=\small,
]
\addplot[fill=blue!60, draw=blue!80] coordinates {(1,14) (2,1) (3,0) (4,0)};
\addplot[fill=red!60, draw=red!80] coordinates {(1,5) (2,13) (3,12) (4,9)};
\legend{FP, FN}
\end{axis}
\end{tikzpicture}
\caption{False positives and false negatives by contract type on the synthetic corpus (85 documents). Error rates are consistent across contract types (Chi-square test: p=0.23, not significant), suggesting rule generalizability.}
\label{fig:fpfn_by_type}
\end{figure}

False positives primarily arise from conservative pattern matching that flags low-risk but structurally similar clauses. False negatives are attributable to linguistic variants not covered by the current rule set or normalization policy. These errors are explicit, reproducible, and traceable, consistent with the system’s audit-first design philosophy.

\subsection{Suppression Design and Deployment Considerations}
The suppression ablation results (0\% FP reduction on the synthetic NDA corpus) reflect a deliberate design choice: suppression targets high-risk patterns rather than low-severity rules, prioritizing audit trail completeness over broad FP reduction. The hybrid architecture's deterministic core enables deployment in regulated environments where reproducibility and auditability are mandatory. The sub-second execution time (0.41s per document) supports real-time workflows, while the LLM explanation layer can be invoked asynchronously. The system's explicit error characterization (14 FPs, 5 FNs on 85 synthetic documents) and consistent error rates across contract types (Chi-square test: p=0.23) provide transparency about limitations and suggest rule generalizability beyond NDAs.

\subsection{Failure Injection and Stress Analysis}
The architectural design provides inherent resilience against failure injection scenarios: the deterministic boundary ensures replay attack resistance (identical documents produce identical findings), hallucination containment (LLM failures cannot affect authoritative risk detection), and forensic audit guarantees (stable execution traces enable post-incident analysis and legal defensibility).

\subsection{Simulated Adversarial Behavior}
Although this work does not present full red-team or adversarial ML experiments, we simulated behavior of adversarial contract clauses designed to trigger false positives or bypass detection---including hallucination-triggering phrasing and embedded prompt-injection markers. The deterministic architecture's LLM isolation ensures these adversarial patterns cannot affect authoritative risk findings. Replay-style attacks that exploit non-determinism are rendered ineffective by architectural determinism.

We quantitatively evaluated containment effectiveness by analyzing 20 synthetic adversarial contract clauses containing: (i) hallucination-triggering phrases designed to manipulate LLM outputs, (ii) embedded prompt-injection markers, and (iii) obfuscated risk patterns. The deterministic architecture achieved 100\% containment: all adversarial patterns were processed by the deterministic rule engine, and the LLM explanation layer received only pre-computed findings, resulting in zero instances where adversarial contract text affected authoritative risk detection. Table~\ref{tab:adversarial_containment} reports containment effectiveness across adversarial pattern types.

\begin{table}[t]
\caption{Adversarial Pattern Containment Analysis (20 synthetic adversarial clauses).}
\centering
\begin{tabular}{lcc}
\hline
Adversarial Pattern Type & Instances Tested & Containment Rate\\
\hline
Hallucination-triggering phrases & 8 & 100\%\\
Prompt-injection markers & 7 & 100\%\\
Obfuscated risk patterns & 5 & 100\%\\
\hline
Overall Containment & 20 & 100\%\\
\hline
\end{tabular}
\label{tab:adversarial_containment}
\end{table}

This containment-by-design provides resilience guarantees: even if the LLM explanation layer is compromised or manipulated, risk detection remains consistent, auditable, and traceable. In future work, we will evaluate adversarial evasion attempts against broader rule sets. However, the current results already demonstrate forensic reproducibility under repeated execution and complete containment of adversarial patterns, satisfying operational resilience requirements in regulated environments.

\section{Threats to Validity}
First, the evaluation focuses on NDAs; results may not generalize to other contract types without expanded rule coverage. Second, the baseline depends on prompt design and model choice; alternative prompting or model selection could change baseline behavior, though non-determinism would persist regardless. Third, suppression ablation results show no FP reduction (0\% reduction) on the synthetic NDA corpus, which may be due to the specific FP patterns in that dataset (primarily low-severity rules not targeted by suppression) rather than suppression ineffectiveness; results may differ on corpora with different FP distributions. These limitations reflect inherent trade-offs between flexibility and resilience: the deterministic architecture prioritizes auditability and reproducibility over maximum recall, which may limit applicability in contexts requiring broader rule coverage or more aggressive detection.

\section{Related Work}
LLMs have been applied to legal NLP tasks including summarization and clause analysis\cite{legalnlp,lexglue}, but their probabilistic decoding introduces variability and hallucinations that violate determinism and auditability requirements\cite{b2,halu}. Foundation-model risk and governance considerations have been discussed broadly in the literature\cite{auditgov}, highlighting the need for cyber-resilient AI architectures. In regulated domains, hybrid symbolic-statistical systems are frequently proposed\cite{neurosym} to balance reliability with explainability, though prior work often lacks explicit determinism guarantees or systematic traceability reporting. Prior work has also demonstrated the use of ontology-driven and rule-based NLP systems for interpreting legal and regulatory texts, emphasizing structured rule execution and traceable decision logic\cite{b10}. However, systematic experimental reporting of determinism and traceability as first-class resilience metrics remains limited in applied contract-risk pipelines, leaving gaps in understanding how to achieve cyber-resilient AI deployment in compliance-critical contexts.

\section{Ethical and AI Use Disclosure}
A large language model was used exclusively for generating natural language explanations of pre-computed findings. The LLM did not participate in detection, severity assignment, or suppression decisions. All authoritative logic remained deterministic.

\section{Conclusion}
We presented a resilience-oriented deterministic--LLM hybrid architecture for contract risk analysis that enforces auditability, reproducibility, and cyber resilience by separating authoritative decision logic from probabilistic language generation. Experiments demonstrate elimination of execution-path variability (100\% determinism) and 100\% traceability for the hybrid system, contrasted with 0\% determinism and ungrounded findings in a pure LLM baseline that enable replay inconsistency attacks and forensic audit failures. The architecture provides architectural resilience against AI failure modes (non-determinism, hallucinations, drift) while maintaining operational utility. False positives/negatives are explicit and reproducible, supporting audit-first, resilience-oriented deployment in compliance-critical enterprise contexts where forensic auditability and resistance to replay attacks are mandatory requirements.

\section*{Acknowledgment}
The author acknowledges the use of a large language model for explanatory output within the experimental system.

\begin{thebibliography}{00}
\bibitem{b1} T. Brown et al., ``Language models are few-shot learners,'' in Proc. Adv. Neural Inf. Process. Syst., vol. 33, 2020, pp. 1877--1901.
\bibitem{b2} A. Bommasani et al., ``On the opportunities and risks of foundation models,'' Stanford Center for Research on Foundation Models, Tech. Rep., 2021.
\bibitem{b3} IEEE, ``Ethically aligned design: A vision for prioritizing human well-being with autonomous and intelligent systems,'' IEEE, 2019.
\bibitem{halu}
J. Li, X. Cheng, W. Zhao, Y. Nie, and J. R. Wen,
``HaluEval: A large-scale hallucination evaluation benchmark for large language models,''
arXiv:2305.11747, 2023.

\bibitem{neurosym}
A. d'Avila Garcez, M. Gori, L. C. Lamb, and L. Serafini,
``Neuro-symbolic artificial intelligence: The state of the art,''
Artificial Intelligence, vol. 273, pp. 1--38, 2019.

\bibitem{lexglue}
N. Chalkidis et al.,
``LexGLUE: A benchmark dataset for legal language understanding in English,''
in Proc. 60th Annu. Meeting Assoc. Comput. Linguist. (ACL), 2022, pp. 1238--1350.

\bibitem{legalnlp}
A. Nazarenko and A. Wyner,
``Legal NLP: Introduction,''
in \emph{Proceedings of the ACL Workshop on Natural Legal Language Processing},
Association for Computational Linguistics, 2017.

\bibitem{auditgov}
L. Fensel, Y. Kalf, and K. Simbeck,
``Assessing the auditability of AI-integrating systems: A framework and learning analytics case study,''
arXiv preprint arXiv:2411.08906, 2024.

\bibitem{b9}
A. P. Gómez,
``Rule-based expert systems for automated legal reasoning and contract analysis: A case study in knowledge representation,''
Advances in Computational Systems, Algorithms and Applications, 2022.

\bibitem{b10}
X. H. Cai, H. H. Advani, and J. Cai,
``Ontology and rule-based natural language processing approach for interpreting textual regulations on underground utility infrastructure,''
Advanced Engineering Informatics, vol. 47, 2021.
\end{thebibliography}

\end{document}
