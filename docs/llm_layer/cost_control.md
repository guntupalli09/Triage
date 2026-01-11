# Cost Control

## Cost Management Strategy

The LLM layer is designed to minimize API costs while maintaining quality.

## Token Optimization

### Input Optimization

**Strategy**: Never send contract text.

**Implementation**:
- Only deterministic findings sent to LLM
- Findings grouped by rule (reduces repetition)
- Up to 2 excerpts per rule shown
- Truncated if findings are too numerous

**Result**: Input tokens: ~500-1000 per analysis (vs. 10,000+ for full contract)

### Output Optimization

**Strategy**: Constrain output size.

**Implementation**:
- Max 5 summary bullets
- Max 6 top issues
- Max 6 missing sections
- Structured JSON (no verbose explanations)

**Result**: Output tokens: ~300-500 per analysis

### Model Selection

**Strategy**: Use cost-effective model.

**Implementation**:
- Model: `gpt-4o-mini`
- Temperature: `0.2` (low, for consistency)
- JSON mode: Enforced

**Result**: ~$0.001-0.002 per analysis (at current pricing)

## Cost Estimates

### Per Analysis

- **Input tokens**: 500-1000
- **Output tokens**: 300-500
- **Total tokens**: 800-1500
- **Cost**: ~$0.001-0.002

### Monthly Estimates

Assuming 1000 analyses/month:
- **Total tokens**: 800,000-1,500,000
- **Cost**: ~$1-2/month

### Fallback Rate

- **Expected fallback**: 5-10% of analyses
- **Fallback cost**: $0 (no API call)
- **Savings**: ~$0.10-0.20/month per 1000 analyses

## Cost Monitoring

### What to Monitor

1. **API call rate**: How many analyses use LLM
2. **Fallback rate**: How often fallback is used
3. **Token usage**: Average tokens per analysis
4. **Cost per analysis**: Track over time

### Recommendations

- Set up OpenAI usage alerts
- Monitor fallback rate (high rate may indicate API issues)
- Track cost trends (identify optimization opportunities)

## Cost Optimization Techniques

### 1. Finding Grouping

**Technique**: Group multiple matches of same rule.

**Savings**: Reduces input tokens by ~30-50%

### 2. Excerpt Limiting

**Technique**: Show max 2 excerpts per rule.

**Savings**: Prevents token explosion on high-match rules

### 3. Output Constraints

**Technique**: Limit output size (max bullets, issues, sections).

**Savings**: Reduces output tokens by ~20-30%

### 4. Fallback Strategy

**Technique**: Automatic fallback when API fails.

**Savings**: No cost for failed API calls

## Scaling Considerations

### Linear Scaling

Cost scales linearly with:
- Number of analyses
- Average contract size (affects finding count)
- LLM availability (affects fallback rate)

### Optimization Opportunities

1. **Caching**: Cache explanations for common findings (future)
2. **Batching**: Batch multiple analyses (future)
3. **Model selection**: Use cheaper models for simple cases (future)

## Cost vs. Quality Trade-offs

### Current Balance

- **Quality**: High (gpt-4o-mini provides good explanations)
- **Cost**: Low (~$0.001-0.002 per analysis)
- **Reliability**: High (fallback available)

### Potential Adjustments

- **Lower cost**: Use cheaper model (may reduce quality)
- **Higher quality**: Use more expensive model (increases cost)
- **Current choice**: Optimal balance

## Budget Planning

### For Production

Estimate monthly costs:
- **Analyses/month**: Estimate based on usage
- **Cost per analysis**: ~$0.001-0.002
- **Buffer**: Add 20% for variance
- **Total**: `analyses × cost × 1.2`

### Example

- 1000 analyses/month
- $0.0015 average cost
- 20% buffer
- **Monthly budget**: $1.80

## Cost Transparency

Costs are transparent:
- No hidden fees
- Pay-per-use model
- Clear pricing (Stripe checkout shows amount)
- No subscription overhead

## Future Cost Management

Potential enhancements:
- **Usage analytics**: Track costs per user (if accounts added)
- **Cost alerts**: Notify when approaching budget
- **Optimization suggestions**: Recommend cost-saving changes
- **Caching layer**: Cache common explanations

These would maintain cost control while scaling.
