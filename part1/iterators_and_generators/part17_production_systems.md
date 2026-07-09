# Part 17 — Production Systems

## 17.1 FastAPI Streaming Responses

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

async def generate_llm_tokens(prompt: str):
    """Stream LLM output token by token."""
    async for token in llm.stream(prompt):
        yield f"data: {token}\n\n"
        await asyncio.sleep(0)  # Yield control to event loop

@app.get("/chat")
async def chat(prompt: str):
    return StreamingResponse(
        generate_llm_tokens(prompt),
        media_type="text/event-stream"
    )
```

## 17.2 Django ORM QuerySet Iteration

```python
# Django QuerySets are LAZY:
users = User.objects.filter(active=True)  # No DB query yet!
# Query executes on iteration:
for user in users:  # NOW the SQL is sent
    process(user)

# For large tables: iterator() avoids loading all rows:
for user in User.objects.filter(active=True).iterator(chunk_size=2000):
    process(user)  # Fetches 2000 rows at a time from DB cursor
```

## 17.3 pandas chunked Reading

```python
import pandas as pd

# Read 100GB CSV in chunks:
for chunk in pd.read_csv("huge.csv", chunksize=100_000):
    # chunk is a DataFrame of 100K rows
    process(chunk)
    # Previous chunk can be GC'd — constant memory!
```

## 17.4 Kafka Consumer (Infinite Stream)

```python
from kafka import KafkaConsumer

consumer = KafkaConsumer("my-topic", bootstrap_servers="localhost:9092")
# consumer is an INFINITE iterator:
for message in consumer:  # Never ends! Waits for new messages.
    process(message.value)
```

## 17.5 Large File Processing

```python
def process_log(path):
    """Process multi-GB log file with constant memory."""
    with open(path) as f:
        # Chain of generators — O(1) memory:
        lines = (line.strip() for line in f)
        json_records = (json.loads(line) for line in lines if line)
        errors = (r for r in json_records if r["level"] == "ERROR")
        recent = (r for r in errors if r["timestamp"] > cutoff)
        
        for record in recent:
            alert(record)
```

## 17.6 LLM Token Streaming

```python
# OpenAI streaming:
async def stream_chat(messages):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4", messages=messages, stream=True
    )
    async for chunk in response:
        delta = chunk.choices[0].delta
        if hasattr(delta, "content"):
            yield delta.content  # Yield each token as it arrives

# Usage:
async for token in stream_chat(messages):
    print(token, end="", flush=True)  # Real-time output!
```

## 17.7 Interview Questions — Part 17

**Q1**: How does FastAPI stream responses using generators? **A**: StreamingResponse accepts an async generator. Each yielded chunk is sent to the client immediately over the HTTP connection. No buffering of the entire response.

**Q2**: Why does Django's `.iterator()` method exist? **A**: Normal QuerySet iteration loads ALL rows into memory (for caching). `.iterator()` uses a server-side cursor, fetching in chunks — constant memory for large tables.

**Q3**: How do you process a 100GB CSV file? **A**: `pd.read_csv(path, chunksize=N)` returns an iterator of DataFrames. Each chunk is processed then freed. Or: use a generator that reads line-by-line.
