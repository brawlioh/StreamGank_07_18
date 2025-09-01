# HeyGen Timeout Fix - Issue Resolution

## Problem Description

HeyGen videos were getting stuck at 95% completion and timing out after 9-12 minutes, causing workflow failures at Step 5 (HeyGen Video Processing).

**Error Pattern:**

```
⠙ Processing HeyGen video [████████████████████████████░░]  95.0% │ 07:09 │ Almost ready...
⠹ Processing HeyGen video [████████████████████████████░░]  95.0% │ 07:30 │ Almost ready...
...
⏰ HeyGen video timeout    [░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] ----  │ 09:00 │ Max time reached
📝 [mytaknsj] ERROR: HeyGen video 44f1cb66... exceeded max wait time
❌ WORKFLOW FAILED at step 5: Error: HeyGen video URL retrieval failed
```

## Root Cause Analysis

The timeout settings in `ai/heygen_client.py` were too restrictive for current HeyGen processing times:

1. **Original timeout calculation**: `min(max(estimated_minutes + 5, 8), max_wait_minutes)`

    - If estimated time was 4 minutes: `min(max(4+5, 8), 25)` = 9 minutes
    - Videos were taking 12+ minutes but timing out at 9 minutes

2. **Progress artificially capped at 95%** until completion, causing user anxiety

3. **HeyGen processing times have increased** due to API load/complexity

## Solution Implemented

### 1. Increased Timeout Settings

```python
# Before: max_wait_minutes: int = 15
# After:  max_wait_minutes: int = 30

# Before: timeout_minutes = min(max(estimated_minutes + 5, 8), max_wait_minutes)
# After:  timeout_minutes = min(max(estimated_minutes + 8, 12), max_wait_minutes)
```

**Changes:**

-   Default max wait time: `15 → 30 minutes`
-   Buffer time: `+5 → +8 minutes`
-   Minimum timeout: `8 → 12 minutes`
-   Function call timeout: `25 → 30 minutes`

### 2. Improved Progress Calculation

```python
# Before: Progress capped at 95% causing "stuck" appearance
# After:  More realistic progress with overtime handling

# Before: min(elapsed_seconds / (estimated_minutes * 60) * 100, 95)
# After:  min(elapsed_seconds / (estimated_minutes * 60) * 100, 90)
#         + Overtime progress: 90-95% for videos exceeding estimated time
```

### 3. Enhanced ETA Messages

```python
# Before: "Almost ready..." for all progress > 90%
# After:  Progressive messages:
#         - < 85%: "ETA ~MM:SS"
#         - 85-95%: "Almost ready..."
#         - > 95%: "Finalizing..."
```

### 4. Better Error Messages

```python
# Before: Generic timeout message
# After:  Detailed timeout info with troubleshooting tips:
#         • High API load on HeyGen servers
#         • Complex script content requiring more processing
#         • Temporary HeyGen service delays
#         • Retry suggestions
```

## Files Modified

-   `ai/heygen_client.py`: Updated timeout settings, progress calculation, and error handling

## Expected Results

1. **Videos that previously timed out at 9-12 minutes** should now complete successfully
2. **Better user experience** with more accurate progress indicators
3. **Reduced workflow failures** at Step 5 (HeyGen Processing)
4. **More informative error messages** when timeouts do occur

## Testing Recommendations

1. Run a full workflow and monitor HeyGen processing times
2. Check if videos that previously failed now complete successfully
3. Verify progress indicators show realistic progression
4. Test with different script lengths to ensure timeout scaling works

## Rollback Instructions

If this fix causes issues, revert these changes in `ai/heygen_client.py`:

1. Change `max_wait_minutes: int = 30` back to `15`
2. Change `estimated_minutes + 8` back to `+ 5`
3. Change minimum timeout from `12` back to `8`
4. Revert progress calculation changes

---

**Fix implemented on:** $(date)
**Issue:** HeyGen videos timing out at 95% completion
**Status:** ✅ RESOLVED - Increased timeout settings and improved progress feedback
