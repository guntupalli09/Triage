# NDA Dataset

This directory contains 30 NDA documents for experimentation:
- **15 Public NDAs**: Template-based documents recreated from common NDA boilerplate language
- **15 Synthetic NDAs**: Programmatically generated with controlled clause variations

## File Structure

Each document has:
- `<doc_id>.txt`: The NDA text
- `<doc_id>.meta.json`: Metadata (type, source, creation date)
- `<doc_id>.truth.json`: Ground truth labels (synthetic docs only)

## Public NDAs

Public NDAs are marked with `"public_template_recreated": true` in metadata, indicating they are recreated from well-known template language rather than downloaded from external sources.

## Synthetic NDAs

Synthetic NDAs include ground truth labels specifying:
- `expected_rule_ids_present`: Rule IDs that should be detected
- `expected_rule_ids_absent`: Rule IDs that should NOT be detected

These are used for false positive/false negative evaluation.

## Generation

Run:
```bash
python experiments/data/build_public_ndas.py
python experiments/data/build_synthetic_ndas.py
```
