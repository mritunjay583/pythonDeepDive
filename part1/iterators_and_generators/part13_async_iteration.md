# Part 13 — Async Iteration

## 13.1 The Problem: Iteration Over I/O

```python
# Synchronous iteration blocks the event loop:
for row in database.query("SELECT * FROM users"):  # BLOCKS on each row!
    process(row)

# We need: iterate without blocking, let other tasks run between items.
```

## 13.2 The Async Iterator Protocol (PEP 492, PEP 525)

```python
class AsyncIterator:
    def __aiter__(self):
        return self  # Return self (like sync iterators)
    
    async def __anext__(self):
        """Return next value or raise StopAsyncIteration."""
        data = await self._fetch_next()  # Can await I/O!
        if data is None:
            raise StopAsyncIteration
        return data
```

```python
# Usage with async for:
async for item in async_iterable:
    await process(item)

# Desugars to:
_iter = aiter(async_iterable)  # calls __aiter__
while True:
    try:
        item = await anext(_iter)  # calls __anext__ (awaitable!)
    except StopAsyncIteration:
        break
    await process(item)
```

## 13.3 Async Generators (PEP 525)

```python
async def fetch_pages(urls):
    """Async generator: yields pages one at a time."""
    async with aiohttp.ClientSession() as session:
        for url in urls:
            async with session.get(url) as response:
                yield await response.text()  # async yield!

# Usage:
async for page in fetch_pages(url_list):
    process(page)
```

## 13.4 Async Comprehensions (PEP 530)

```python
# Async list comprehension:
results = [await fetch(url) async for url in url_generator]

# Async generator expression:
pages = (await fetch(url) async for url in url_generator)
```

## 13.5 Production Example: FastAPI Streaming

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

async def generate_data():
    """Async generator for streaming response."""
    for i in range(1000):
        await asyncio.sleep(0.01)  # Simulate async work
        yield f"data: {i}\n\n"     # Server-Sent Event format

@app.get("/stream")
async def stream():
    return StreamingResponse(
        generate_data(),
        media_type="text/event-stream"
    )
# Client receives data as it's generated — no buffering entire response!
```

## 13.6 Database Streaming

```python
# SQLAlchemy async streaming:
async def stream_users():
    async with async_session() as session:
        result = await session.stream(select(User))
        async for row in result:
            yield row.User

# Process millions of rows with constant memory:
async for user in stream_users():
    await process(user)
```

## 13.7 Interview Questions — Part 13

**Q1**: What's the difference between `__next__` and `__anext__`? **A**: `__next__` returns a value synchronously. `__anext__` returns an awaitable that resolves to the next value. Allows the event loop to run other tasks while waiting.

**Q2**: What exception terminates async iteration? **A**: `StopAsyncIteration` (not StopIteration!). Different exception type because the async iteration protocol is separate.

**Q3**: What is an async generator? **A**: A function with both `async def` and `yield`. Calling it returns an async generator object. Used with `async for`. Each yield point can await I/O before yielding.

**Q4**: How does FastAPI use async generators for streaming? **A**: StreamingResponse accepts an async generator. Each yielded chunk is sent to the client immediately. The response streams progressively — no buffering.
