# Rate Limit Handling Guide

## Overview

Anthropic's Claude API has rate limits that vary by organization tier. This guide explains how the Artisan Agent handles rate limits and how to configure it for your specific limits.

---

## Understanding Anthropic Rate Limits

### Common Rate Limit Tiers

| Tier | Input Tokens/Min | Output Tokens/Min | Requests/Min |
|------|-----------------|-------------------|--------------|
| **Free/Trial** | 10,000 | 10,000 | 50 |
| **Build Tier 1** | 30,000 | 30,000 | 50 |
| **Build Tier 2** | 80,000 | 80,000 | 100 |
| **Build Tier 3** | 400,000 | 400,000 | 500 |
| **Scale** | 2,000,000 | 2,000,000 | 2,000 |

**Your current limit:** Check error messages or visit [Anthropic Console](https://console.anthropic.com/settings/limits)

### Rate Limit Window

- Rate limits are calculated per **sliding 60-second window**
- If you hit the limit, you must wait for the window to reset
- Example: If you use 10,000 tokens at 12:00:00, you can't use more until 12:01:00

---

## How Artisan Agent Handles Rate Limits

### 1. Automatic Retry with Exponential Backoff

When a rate limit error occurs, the agent automatically retries with increasing wait times:

```
Attempt 1: Wait 15 seconds
Attempt 2: Wait 30 seconds
Attempt 3: Wait 60 seconds  ← Full rate limit window reset
Attempt 4: Wait 120 seconds
Attempt 5: Wait 240 seconds (final attempt)
```

**Why 60 seconds is important:** After 60 seconds, the entire rate limit window has reset, guaranteeing you can proceed.

### 2. Step Delay Prevention

A small delay (default: 2 seconds) between modeling steps prevents rapid-fire API calls that could exhaust your rate limit.

### 3. Token Usage Optimization

Recent optimizations reduce token consumption:
- Vision model max_tokens: 1024 → 512 (50% reduction)
- Context history: Last 3 items → Last 2 items
- Feedback truncation: 200 chars → 150 chars

---

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Maximum retry attempts (default: 5)
RATE_LIMIT_MAX_RETRIES=5

# Base wait time in seconds (default: 15)
# Creates exponential backoff: 15s, 30s, 60s, 120s, 240s
RATE_LIMIT_BASE_WAIT=15

# Delay between steps in seconds (default: 2.0)
# Set to 0 to disable, but may hit limits faster
RATE_LIMIT_STEP_DELAY=2.0
```

### Recommended Settings by Tier

#### Free/Trial Tier (10,000 tokens/min)
```bash
RATE_LIMIT_MAX_RETRIES=5
RATE_LIMIT_BASE_WAIT=20    # More conservative
RATE_LIMIT_STEP_DELAY=3.0  # Slower pacing
```

#### Build Tier 1 (30,000 tokens/min)
```bash
RATE_LIMIT_MAX_RETRIES=5
RATE_LIMIT_BASE_WAIT=15    # Default
RATE_LIMIT_STEP_DELAY=2.0  # Default
```

#### Build Tier 2+ (80,000+ tokens/min)
```bash
RATE_LIMIT_MAX_RETRIES=5
RATE_LIMIT_BASE_WAIT=10    # Faster recovery
RATE_LIMIT_STEP_DELAY=1.0  # Minimal delay
```

#### Scale Tier (2M+ tokens/min)
```bash
RATE_LIMIT_MAX_RETRIES=3
RATE_LIMIT_BASE_WAIT=5     # Quick recovery
RATE_LIMIT_STEP_DELAY=0.0  # No delay needed
```

---

## Troubleshooting Rate Limit Errors

### Error Example

```
⏳ Rate limit hit (attempt 1/5). Waiting 15s before retry... 
   (Tip: Rate limit window resets after 60s)
```

### Common Scenarios

#### Scenario 1: Rapid Sequential Steps

**Problem:** Multiple steps execute quickly, exhausting rate limit

**Solution:**
```bash
# Increase step delay
RATE_LIMIT_STEP_DELAY=3.0
```

#### Scenario 2: Large Prompts

**Problem:** Comprehensive prompts use many tokens per request

**Solution:**
- Use `detail_level: "moderate"` instead of `"comprehensive"` in prompts
- Or increase base wait time:
```bash
RATE_LIMIT_BASE_WAIT=20
```

#### Scenario 3: Refinement Loop Triggering

**Problem:** Refinement steps double API calls per step

**Solution:**
- Disable refinement if not critical:
```python
# In your JSON file
{
    "enable_refinement_steps": false
}
```
- Or reduce refinement attempts:
```bash
REFINEMENT_STEPS=1
```

#### Scenario 4: Multiple Concurrent Tasks

**Problem:** Running multiple batch tasks simultaneously

**Solution:**
- Run tasks sequentially instead of parallel
- Or upgrade your Anthropic tier

---

## Monitoring Rate Limit Usage

### Log Messages to Watch

**Rate Limit Hit:**
```
⏳ Rate limit hit (attempt 1/5). Waiting 15s before retry...
```

**Vision Analysis:**
```
🔍 Vision analysis complete
```
This uses a separate API call - watch for these in quick succession.

**Step Completion:**
```
Step 5/20: Add materials to geometry
```
Each step may trigger 1-3 API calls (plan → execute → vision).

### Calculating Token Usage

Approximate token usage per step:

| Operation | Input Tokens | Output Tokens |
|-----------|--------------|---------------|
| Planning | 2,000-3,000 | 500-1,000 |
| Execution | 1,500-2,500 | 300-800 |
| Vision Analysis | 1,500-2,000 | 200-400 |
| Refinement | 2,000-3,000 | 400-1,000 |

**Total per step (no refinement):** ~5,000-7,500 tokens
**Total per step (with refinement):** ~8,000-12,000 tokens

**Example:** For 10,000 tokens/min limit:
- **Without refinement:** ~1.3 steps/minute
- **With refinement:** ~0.8 steps/minute

---

## Best Practices

### 1. Choose Appropriate Detail Level

```python
# Lower token usage
detail_level = "moderate"  # 500-1,000 words

# Higher token usage
detail_level = "comprehensive"  # 1,000+ words
```

### 2. Use Deterministic Session IDs

Allows resuming from where you left off:

```python
agent.run(requirement_file, use_deterministic_session=True)
```

### 3. Monitor First Few Steps

Watch logs during first 2-3 steps to gauge your token consumption rate.

### 4. Batch Tasks During Off-Peak Hours

If you have many tasks, run them when rate limits are less likely to be constrained.

### 5. Consider Disabling Refinement for Simple Models

```json
{
    "refined_prompt": "Create a simple cube",
    "enable_refinement_steps": false
}
```

---

## Upgrading Your Rate Limit

### When to Upgrade

Consider upgrading if you:
- Frequently hit rate limits (>3 retries per task)
- Run large batch jobs
- Need faster turnaround times
- Use comprehensive detail level regularly

### How to Upgrade

1. Visit [Anthropic Console](https://console.anthropic.com/settings/limits)
2. Check your current tier and usage
3. Click "Request Limit Increase" or contact sales
4. Or visit [Contact Sales](https://www.anthropic.com/contact-sales)

### Expected Response Times

| Tier | Typical Approval Time |
|------|----------------------|
| Build Tier 1 | Instant (automated) |
| Build Tier 2 | 1-2 business days |
| Build Tier 3 | 2-3 business days |
| Scale | 3-5 business days |

---

## Advanced Configuration

### Disable Retry for Testing

```bash
# Only try once, fail immediately
RATE_LIMIT_MAX_RETRIES=1
RATE_LIMIT_BASE_WAIT=0
```

### Aggressive Retry for Production

```bash
# More retries with longer waits
RATE_LIMIT_MAX_RETRIES=7
RATE_LIMIT_BASE_WAIT=20
```

### Custom Retry Logic

Modify `artisan_agent.py`:

```python
# Custom wait times (not exponential)
wait_times = [10, 30, 60, 90, 120]  # seconds
wait_time = wait_times[min(attempt, len(wait_times)-1)]
```

---

## Error Messages Explained

### "This request would exceed the rate limit"

**Meaning:** Your request would push you over the limit

**Action:** Wait is automatic, no action needed

### "Rate limit exceeded"

**Meaning:** You've already exceeded the limit

**Action:** Wait for 60-second window to reset

### "429 - rate_limit_error"

**Meaning:** HTTP 429 status code for rate limiting

**Action:** Automatic retry will handle this

---

## Summary

✅ **Rate limit handling is automatic** - no manual intervention needed

✅ **Configurable wait times** - adjust for your tier

✅ **Smart exponential backoff** - 60s wait guarantees reset

✅ **Step delays** - prevent rapid-fire API calls

✅ **Token optimizations** - reduced usage by 30-40%

**Most users should use default settings.** Only adjust if you:
- Have a different rate limit tier
- Frequently see retry attempts >3
- Need faster execution and have higher limits

For questions or issues, check the logs for detailed retry information!
