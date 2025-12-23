# Deep Linking Implementation - Technical Documentation

## Overview

This document describes the implementation of deep linking from search results to specific messages in conversation view, including auto-scroll functionality and the technical challenges encountered with Streamlit.

## Implementation

### Search Results Links

**File:** `streamlit_app/pages/search.py`

Search results include links with `message_index` query parameter:

```python
view_url = f"conversation?session_id={session_id}&message_index={message_index}"
st.markdown(f"[View in Conversation →]({view_url})")
```

### Auto-Scroll Mechanism

**File:** `streamlit_app/pages/conversation.py`

When a user clicks a search result link, the conversation page:

1. Reads the `message_index` from query parameters
2. Applies `message-highlight` CSS class to the target message
3. Uses `st.components.v1.html()` to inject JavaScript that scrolls to the message

```python
# Read query parameter
query_params = st.query_params
if "message_index" in query_params:
    target_message_index = int(query_params["message_index"])

# Apply highlight class to target message
is_target = target_message_index is not None and msg.message_index == target_message_index
container_class = "message-highlight" if is_target else ""
st.markdown(f'<div id="msg-{msg.message_index}" class="{container_class}">', unsafe_allow_html=True)

# Auto-scroll to target message
if target_message_index is not None:
    import streamlit.components.v1 as components
    components.html(f"""
    <script>
        setTimeout(function() {{
            const targetElement = window.parent.document.getElementById('msg-{target_message_index}');
            if (targetElement) {{
                targetElement.scrollIntoView({{ behavior: 'instant', block: 'center' }});
            }}
        }}, 100);
    </script>
    """, height=0)
```

### CSS Highlight Animation

Target messages get a gold border and yellow background that fades over 3 seconds:

```css
.message-highlight {
    border-left: 4px solid #ffd700;
    padding-left: 1rem;
    margin-left: -1rem;
    background-color: rgba(255, 215, 0, 0.15);
    animation: fadeHighlight 3s ease-in-out;
}

@keyframes fadeHighlight {
    0% {
        background-color: rgba(255, 215, 0, 0.3);
    }
    70% {
        background-color: rgba(255, 215, 0, 0.3);
    }
    100% {
        background-color: rgba(255, 215, 0, 0.15);
    }
}
```

## Streamlit Limitations & Challenges

### 1. st.markdown() Sanitizes JavaScript

**Problem:** Streamlit strips `<script>` tags from `st.markdown()` for security reasons.

**Evidence:**
```python
# This does NOT work - script is sanitized
st.markdown(f"""
<script>
    document.getElementById('msg-{target_message_index}').scrollIntoView();
</script>
""", unsafe_allow_html=True)
```

**Solution:** Must use `st.components.v1.html()` which creates an iframe that can execute JavaScript.

```python
# This WORKS - component iframe executes JavaScript
import streamlit.components.v1 as components
components.html(f"""
<script>
    // JavaScript executes here
</script>
""", height=0)
```

### 2. Component Iframes Load After Page Render

**Problem:** `st.components.v1.html()` creates sandboxed iframes that load at the end of the page render cycle, causing a noticeable delay before scrolling occurs.

**Timeline:**
1. Page content renders (fast, ~300ms for 1000+ messages)
2. User sees page at top position
3. Component iframe loads (200-400ms delay)
4. JavaScript executes and scrolls to target message

**Impact:** Users experience a delay where the page sits at the top before jumping to the target message. This delay is unavoidable with Streamlit's architecture.

**Evidence from console logs:**
```
[SCROLL] Component iframe script loaded at: 2025-12-21T03:14:55.114Z
[SCROLL] Parent document readyState: complete
[SCROLL] Timeout callback fired after 201.90 ms
```

The component loads ~200ms after the page is already complete.

### 3. Sandboxed Iframe Security Restrictions

**Problem:** Component iframes are sandboxed and cannot navigate or modify the parent window.

**Failed Approach #1: Setting window.location.hash**

```javascript
// This fails with SecurityError
window.parent.location.hash = '#msg-1338';
```

**Error:**
```
Uncaught SecurityError: Failed to set the 'hash' property on 'Location':
The current window does not have permission to navigate the target frame to
'http://localhost:8501/conversation?...#msg-1338'.

The frame attempting navigation of the top-level window is sandboxed,
but the flag of 'allow-top-navigation' or 'allow-top-navigation-by-user-activation' is not set.
```

**Failed Approach #2: Using window.parent.scrollTo()**

```javascript
// This fails - cross-origin restriction
window.parent.scrollTo({ top: 376907, behavior: 'instant' });
```

**Evidence from console logs:**
```
[SCROLL] Target absolute position: 377223.72 px
[SCROLL] Scroll target (centered): 376907.22 px
[SCROLL] After scroll - scrollY: 0  // ← Didn't scroll!
```

The scrollY remained at 0 even after calling `scrollTo()`.

**What Works: element.scrollIntoView()**

The iframe CAN access parent document elements and call methods on them:

```javascript
// This WORKS
const targetElement = window.parent.document.getElementById('msg-1338');
targetElement.scrollIntoView({ behavior: 'instant', block: 'center' });
```

This is allowed because we're calling a method on a DOM element, not navigating the window.

## Approaches Tried

### ✅ Working Solution: scrollIntoView() from Component Iframe

**Implementation:**
```python
components.html(f"""
<script>
    setTimeout(function() {{
        const targetElement = window.parent.document.getElementById('msg-{target_message_index}');
        if (targetElement) {{
            targetElement.scrollIntoView({{ behavior: 'instant', block: 'center' }});
        }}
    }}, 100);
</script>
""", height=0)
```

**Pros:**
- Actually works
- Instant scroll (no animation)
- Centers message in viewport

**Cons:**
- 200-400ms delay waiting for component iframe to load
- Delay is unavoidable with Streamlit architecture

### ❌ Failed: Native HTML Anchor Scrolling

**Attempt:** Include hash in URL and let browser handle scrolling:

```python
# In search.py
view_url = f"conversation?session_id={session_id}&message_index={message_index}#msg-{message_index}"
```

**Why it failed:** The browser only scrolls to a hash anchor when:
1. The page first loads with a hash in the URL, OR
2. The hash changes from one value to another

Since the hash was already present in the URL when the page loaded, trying to set it again via JavaScript did nothing (and also triggered security errors due to sandboxing).

### ❌ Failed: Setting Hash After Page Load

**Attempt:** Don't include hash in URL, set it via JavaScript after page loads:

```javascript
// In component iframe
window.parent.location.hash = '#msg-1338';
```

**Why it failed:** Sandboxed iframes cannot modify `window.location.hash` of the parent window. This is considered navigation and is blocked for security.

**Error:**
```
SecurityError: Failed to set the 'hash' property on 'Location':
The current window does not have permission to navigate the target frame
```

### ❌ Failed: Direct Scroll with scrollTo()

**Attempt:** Calculate scroll position and use `window.parent.scrollTo()`:

```javascript
const rect = targetElement.getBoundingClientRect();
const absoluteTop = rect.top + window.parent.scrollY;
const center = absoluteTop - (window.parent.innerHeight / 2);
window.parent.scrollTo({ top: center, behavior: 'instant' });
```

**Why it failed:** Cross-origin/sandbox restrictions prevent the iframe from calling `scrollTo()` on the parent window.

**Evidence:** scrollY remained 0 even after calling `scrollTo()`.

### ❌ Failed: Inline Script in st.markdown()

**Attempt:** Inject script directly into page using `st.markdown()`:

```python
st.markdown(f"""
<script>
    document.getElementById('msg-{target_message_index}').scrollIntoView();
</script>
""", unsafe_allow_html=True)
```

**Why it failed:** Streamlit sanitizes `<script>` tags in `st.markdown()` for security. The script tag is stripped and never executes.

## Performance Characteristics

### Page Load
- **Full page render:** ~300ms (for 1000+ messages)
- **Component iframe load:** ~200-400ms (after page render)
- **Total time to scroll:** ~500-700ms from click

### Scroll Behavior
- **Instant jump** (no animation) using `behavior: 'instant'`
- **Centered in viewport** using `block: 'center'`
- **Highlight animation** 3-second gold border fade

### Database Query
The `message_index` parameter is used only for scrolling/highlighting. The page still loads all messages for the session, which is fast enough for sessions with 1000+ messages.

## User Experience

1. User searches for a term (e.g., "weather")
2. Search results show matching messages with context snippets
3. User clicks "View in Conversation →" link
4. Conversation page loads and renders all messages quickly
5. Brief delay (~200-400ms) while component iframe loads
6. Page instantly scrolls to target message
7. Target message is highlighted with gold border
8. Highlight fades over 3 seconds

## Future Improvements

### Potential Optimization: Pagination

If the scroll delay becomes unacceptable, pagination could reduce page load time:

```python
# Only load messages around target
messages = db_service.get_messages_around_index(
    session_id=session_id,
    center_index=target_message_index,
    window_size=50  # 25 before, 25 after
)
```

This would:
- ✅ Reduce page render time
- ✅ Reduce component load delay (smaller page)
- ✅ Faster scroll (fewer DOM elements)
- ❌ Require pagination UI for viewing full conversation

### Alternative: Streamlit Fragment API

Streamlit's experimental fragment feature might allow JavaScript execution in the parent page context, but this hasn't been tested yet.

## Key Takeaways

1. **st.markdown() vs st.components.v1.html()**
   - Use `st.markdown()` for static HTML/CSS
   - Use `st.components.v1.html()` when you need JavaScript execution
   - Components have unavoidable load delay

2. **Iframe Sandbox Restrictions**
   - Can read parent document: `window.parent.document.getElementById()`
   - Can call methods on parent elements: `element.scrollIntoView()`
   - Cannot modify parent window: `window.parent.location.hash` ❌
   - Cannot scroll parent window: `window.parent.scrollTo()` ❌

3. **Native Browser Features**
   - HTML anchor scrolling only works on initial page load with hash
   - Setting hash via JavaScript requires navigation permission
   - `scrollIntoView()` is the most reliable cross-browser scroll method

4. **Performance vs Feature Tradeoffs**
   - The 200-400ms delay is acceptable for most use cases
   - If not, pagination is the best alternative
   - Virtual scrolling libraries don't work well with Streamlit's rendering

## References

- Streamlit Components Documentation: https://docs.streamlit.io/develop/concepts/custom-components
- MDN scrollIntoView: https://developer.mozilla.org/en-US/docs/Web/API/Element/scrollIntoView
- HTML Iframe Sandbox: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox
