# Gemini Deep Research Agent API Reference

## Overview

The Gemini Deep Research Agent autonomously plans, executes, and synthesizes multi-step research tasks. Powered by Gemini 3 Pro, it navigates complex information landscapes using web search and your own data to produce detailed, cited reports.

**Key Points:**
- Research tasks can take several minutes to complete
- Must use `background=True` for asynchronous execution
- Available exclusively through the **Interactions API** (not `generate_content`)
- Agent name: `deep-research-pro-preview-12-2025`

## Basic Usage

### Simple Research Task (Polling)

```python
import time
from google import genai

client = genai.Client()

interaction = client.interactions.create(
    input="Research the history of Google TPUs.",
    agent='deep-research-pro-preview-12-2025',
    background=True
)

print(f"Research started: {interaction.id}")

while True:
    interaction = client.interactions.get(interaction.id)
    if interaction.status == "completed":
        print(interaction.outputs[-1].text)
        break
    elif interaction.status == "failed":
        print(f"Research failed: {interaction.error}")
        break
    time.sleep(10)
```

### Streaming with Progress Updates

```python
stream = client.interactions.create(
    input="Research the history of Google TPUs.",
    agent="deep-research-pro-preview-12-2025",
    background=True,
    stream=True,
    agent_config={
        "type": "deep-research",
        "thinking_summaries": "auto"  # Required for progress updates
    }
)

interaction_id = None
last_event_id = None

for chunk in stream:
    if chunk.event_type == "interaction.start":
        interaction_id = chunk.interaction.id
        print(f"Interaction started: {interaction_id}")

    if chunk.event_id:
        last_event_id = chunk.event_id

    if chunk.event_type == "content.delta":
        if chunk.delta.type == "text":
            print(chunk.delta.text, end="", flush=True)
        elif chunk.delta.type == "thought_summary":
            print(f"Thought: {chunk.delta.content.text}", flush=True)

    elif chunk.event_type == "interaction.complete":
        print("\nResearch Complete")
```

## Research with Your Own Data (File Search)

```python
interaction = client.interactions.create(
    input="Compare our 2025 fiscal year report against current public web news.",
    agent="deep-research-pro-preview-12-2025",
    background=True,
    tools=[
        {
            "type": "file_search",
            "file_search_store_names": ['fileSearchStores/my-store-name']
        }
    ]
)
```

## Steerability and Formatting

Control output format through prompt instructions:

```python
prompt = """
Research the competitive landscape of EV batteries.

Format the output as a technical report with the following structure:
1. Executive Summary
2. Key Players (Must include a data table comparing capacity and chemistry)
3. Supply Chain Risks
"""

interaction = client.interactions.create(
    input=prompt,
    agent="deep-research-pro-preview-12-2025",
    background=True
)
```

## Reconnecting to Stream

Handle network interruptions gracefully:

```python
import time
from google import genai

client = genai.Client()

agent_name = 'deep-research-pro-preview-12-2025'
prompt = 'Compare golang SDK test frameworks'

last_event_id = None
interaction_id = None
is_complete = False

def process_stream(event_stream):
    global last_event_id, interaction_id, is_complete
    for event in event_stream:
        if event.event_type == "interaction.start":
            interaction_id = event.interaction.id
            print(f"Interaction started: {interaction_id}")

        if event.event_id:
            last_event_id = event.event_id

        if event.event_type == "content.delta":
            if event.delta.type == "text":
                print(event.delta.text, end="", flush=True)
            elif event.delta.type == "thought_summary":
                print(f"Thought: {event.delta.content.text}", flush=True)

        if event.event_type in ['interaction.complete', 'error']:
            is_complete = True

# 1. Attempt initial streaming request
try:
    print("Starting Research...")
    initial_stream = client.interactions.create(
        input=prompt,
        agent=agent_name,
        background=True,
        stream=True,
        agent_config={
            "type": "deep-research",
            "thinking_summaries": "auto"
        }
    )
    process_stream(initial_stream)
except Exception as e:
    print(f"\nInitial connection dropped: {e}")

# 2. Reconnection Loop
while not is_complete and interaction_id:
    print(f"\nConnection lost. Resuming from event {last_event_id}...")
    time.sleep(2)

    try:
        resume_stream = client.interactions.get(
            id=interaction_id,
            stream=True,
            last_event_id=last_event_id
        )
        process_stream(resume_stream)
    except Exception as e:
        print(f"Reconnection failed, retrying... ({e})")
```

## Follow-up Questions

Continue conversation after research completes:

```python
interaction = client.interactions.create(
    input="Can you elaborate on the second point in the report?",
    model="gemini-3-pro-preview",
    previous_interaction_id="COMPLETED_INTERACTION_ID"
)

print(interaction.outputs[-1].text)
```

## When to Use Deep Research

| Aspect | Standard Chat | Deep Research |
|--------|---------------|---------------|
| Latency | Seconds | Minutes (Async/Background) |
| Process | Generate → Output | Plan → Search → Read → Iterate → Output |
| Output | Conversational text, code, short summaries | Detailed reports, long-form analysis, comparative tables |
| Best For | Chatbots, extraction, creative writing | Market analysis, due diligence, literature reviews, competitive landscaping |

## Limitations

- **Beta status**: Interactions API is in public beta, features may change
- **No custom tools**: Cannot provide custom Function Calling tools or MCP servers
- **No structured output**: Doesn't support human approved planning or structured outputs
- **Max research time**: 60 minutes (most complete in ~20 minutes)
- **Store requirement**: `background=True` requires `store=True`
- **No audio inputs**: Audio inputs not supported

## Best Practices

1. **Prompt for unknowns**: Instruct how to handle missing data
   - "If specific figures for 2025 are not available, explicitly state they are projections"

2. **Provide context**: Ground research with background information or constraints

3. **Use multimodal inputs cautiously**: Increases costs and risks context overflow

## Safety Considerations

- **Prompt injection via files**: Ensure uploaded documents come from trusted sources
- **Web content risks**: Agent may encounter malicious web pages - review citations
- **Exfiltration**: Be cautious combining sensitive internal data with web browsing

## Availability and Pricing

- Available via Interactions API in Google AI Studio and Gemini API
- Google Search tool calls free until January 5th, 2026
- See [Pricing page](https://ai.google.dev/gemini-api/docs/pricing#pricing-for-agents) for rates

## Required Package

```bash
pip install google-genai
```

## Environment Setup

```bash
export GOOGLE_API_KEY="your-api-key"
# Or use Application Default Credentials
```
