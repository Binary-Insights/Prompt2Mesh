# Rate Limit Quick Reference

## 🚨 Getting Rate Limited?

**Don't panic!** The system handles this automatically.

---

## ⚡ Quick Fixes

### For Free/Trial Tier (10,000 tokens/min)

Add to your `.env` file:
```bash
RATE_LIMIT_STEP_DELAY=3.0
RATE_LIMIT_BASE_WAIT=20
```

### For Build Tier (30,000+ tokens/min)

Use defaults - no changes needed!

---

## 🎯 What's Happening

When you see:
```
⏳ Rate limit hit (attempt 1/5). Waiting 15s before retry...
```

The system is:
1. ✅ Automatically retrying
2. ✅ Using exponential backoff
3. ✅ Will wait 60s if needed (guaranteed reset)

**You don't need to do anything!**

---

## 📊 Understanding Your Limits

| Your Error Message Shows | Your Limit |
|-------------------------|-----------|
| "10,000 input tokens per minute" | Free/Trial Tier |
| "30,000 input tokens per minute" | Build Tier 1 |
| "80,000 input tokens per minute" | Build Tier 2 |

---

## 🔧 Environment Variables

**Default (works for most users):**
```bash
RATE_LIMIT_MAX_RETRIES=5
RATE_LIMIT_BASE_WAIT=15
RATE_LIMIT_STEP_DELAY=2.0
```

**Conservative (for low limits):**
```bash
RATE_LIMIT_MAX_RETRIES=5
RATE_LIMIT_BASE_WAIT=20
RATE_LIMIT_STEP_DELAY=3.0
```

**Aggressive (for high limits):**
```bash
RATE_LIMIT_MAX_RETRIES=3
RATE_LIMIT_BASE_WAIT=10
RATE_LIMIT_STEP_DELAY=1.0
```

---

## 💡 Tips to Reduce Rate Limit Hits

1. **Use moderate detail level:**
   ```
   detail_level: "moderate"  # instead of "comprehensive"
   ```

2. **Disable refinement for simple models:**
   ```json
   {
       "enable_refinement_steps": false
   }
   ```

3. **Run fewer tasks simultaneously**

4. **Increase step delay:**
   ```bash
   RATE_LIMIT_STEP_DELAY=5.0
   ```

---

## 🆙 Upgrade Your Limit

Visit: https://console.anthropic.com/settings/limits

Or contact: https://www.anthropic.com/contact-sales

---

## 📖 Full Documentation

See `RATE_LIMIT_GUIDE.md` for complete details.
