# Page Reduction Plan: 7 Pages → 6 Pages
## Strategic Condensation While Preserving Security Improvements

---

## 🎯 TARGET: Reduce by ~1 page (~15% reduction)

---

## ✅ MUST KEEP (Security Critical - Do Not Remove)

1. **Threat Model Section** (Section 3) - Critical for CSR
2. **Attack Scenario Table** (tab:threat_model) - Just added
3. **Adversarial Containment Table** (tab:adversarial_containment) - Just added
4. **Simulated Adversarial Behavior** subsection - Just added
5. **Core experimental results** (Experiments 1-3)
6. **Security language** throughout

---

## 📉 STRATEGIC CUTS (Priority Order)

### **Priority 1: Condense Threat Model** (Save ~0.2 pages)
- Merge "Failure Modes" and "Attack Surfaces" into one subsection
- Reduce bullet point verbosity
- Keep table, reduce prose

### **Priority 2: Merge Experiment 4 into Experiment 1** (Save ~0.3 pages)
- Remove separate Experiment 4 subsection
- Integrate error characterization into Experiment 1 results
- Remove Figure 2 (fpfn_by_type) - data already in tables
- Keep error table, remove figure

### **Priority 3: Condense System Architecture** (Save ~0.2 pages)
- Merge three subsections into one
- Reduce description verbosity
- Keep figure, condense text

### **Priority 4: Condense Discussion** (Save ~0.2 pages)
- Merge "Suppression Design" and "Practical Deployment" 
- Reduce "Failure Injection" verbosity
- Keep adversarial subsection (critical)

### **Priority 5: Condense Background** (Save ~0.1 pages)
- Merge two subsections into one
- Reduce repetition

### **Priority 6: Remove/Reduce Performance Section** (Save ~0.1 pages)
- Merge into Discussion or remove if not critical

---

## TOTAL SAVINGS: ~1.1 pages

---

## IMPLEMENTATION ORDER

1. Remove Figure 2 (fpfn_by_type) - saves space, data in tables
2. Merge Experiment 4 into Experiment 1
3. Condense Threat Model section
4. Condense System Architecture
5. Condense Discussion subsections
6. Condense Background

---

## VERIFICATION

After cuts:
- Threat model: ✅ PRESERVED
- Attack tables: ✅ PRESERVED  
- Adversarial analysis: ✅ PRESERVED
- Core experiments: ✅ PRESERVED
- Security language: ✅ PRESERVED
