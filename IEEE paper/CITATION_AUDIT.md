# Citation Audit Report
## Checking if all bibliography entries are cited in text

---

## Bibliography Items (10 total)

1. ✅ **b1** - Brown et al., 2020
   - **Cited in**: Line 41, 53, 383

2. ✅ **b2** - Bommasani et al., 2021
   - **Cited in**: Line 41, 53, 383

3. ✅ **b3** - IEEE, 2019
   - **Cited in**: Line 41, 381

4. ✅ **halu** - Li et al., 2023
   - **Cited in**: Line 53

5. ✅ **neurosym** - d'Avila Garcez et al., 2019
   - **Cited in**: Line 381

6. ✅ **lexglue** - Chalkidis et al., 2022
   - **Cited in**: Line 53, 383

7. ❌ **legalnlp** - Nazarenko & Wyner, 2017
   - **NOT CITED** - This reference is in the bibliography but never cited in the text

8. ❌ **auditgov** - Fensel et al., 2024
   - **NOT CITED** - This reference is in the bibliography but never cited in the text

9. ❌ **b9** - Gómez, 2022
   - **NOT CITED** - This reference is in the bibliography but never cited in the text

10. ✅ **b10** - Cai et al., 2021
    - **Cited in**: Line 383

---

## Summary

**Cited**: 7 out of 10 references (70%)
**Not Cited**: 3 out of 10 references (30%)

### Unused References:
1. `legalnlp` - Legal NLP: Introduction (Nazarenko & Wyner, 2017)
2. `auditgov` - Assessing the auditability of AI-integrating systems (Fensel et al., 2024)
3. `b9` - Rule-based expert systems for automated legal reasoning (Gómez, 2022)

---

## Recommendation

**Option 1**: Remove unused references (recommended for clean bibliography)
- Remove `legalnlp`, `auditgov`, and `b9` from bibliography
- Update `\begin{thebibliography}{10}` to `\begin{thebibliography}{7}`

**Option 2**: Add citations for these references in appropriate sections
- `legalnlp` could be cited in Background or Related Work sections
- `auditgov` could be cited in Discussion or Related Work sections
- `b9` could be cited in Related Work section (already mentioned in text context)

**Option 3**: Keep them if they're relevant for future work or context (less common)

---

## Action Required

Please decide:
1. Remove the 3 unused references? (Cleaner, more standard)
2. Add citations for them in the text? (If they're relevant)
3. Keep them as-is? (Not recommended for submission)
