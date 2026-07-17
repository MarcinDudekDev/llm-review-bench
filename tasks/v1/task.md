You are reviewing production code. Below is a small FastAPI service (Python 3.12+) that serves a Datastar-driven dashboard via Server-Sent Events. It contains several real bugs — defects that cause exceptions, protocol failures, or incorrect runtime behavior. It also contains code that may look suspicious but is actually correct.

Line numbers are shown for reference only; they are not part of the code.

```
 1  import asyncio
 2  import time
 3  from functools import lru_cache
 4  from fastapi import FastAPI, Request
 5  from fastapi.responses import StreamingResponse
 6
 7  app = FastAPI()
 8  _cache: dict[str, tuple[float, dict]] = {}
 9  _lock = asyncio.Lock()
10  TTL = 30.0
11
12  @lru_cache(maxsize=128)
13  async def fetch_score(slug: str) -> dict:
14      await asyncio.sleep(0.05)  # simulated upstream call
15      return {"slug": slug, "score": len(slug) * 7 % 100}
16
17  async def get_cached(slug: str) -> dict:
18      now = time.monotonic()
19      async with _lock:
20          hit = _cache.get(slug)
21          if hit and now - hit[0] < TTL:
22              return hit[1]
23          val = await fetch_score(slug)
24          _cache[slug] = (now, val)
25          return val
26
27  async def purge_expired() -> int:
28      removed = 0
29      now = time.monotonic()
30      for slug, (ts, _) in _cache.items():
31          if now - ts > TTL:
32              del _cache[slug]
33              removed += 1
34      return removed
35
36  def make_headers(extra: dict = {}) -> dict:
37      extra["Cache-Control"] = "no-store"
38      return extra
39
40  @app.post("/purge")
41  async def purge():
42      asyncio.create_task(purge_expired())
43      return {"queued": True}
44
45  @app.get("/updates")
46  async def updates(request: Request):
47      async def stream():
48          try:
49              while True:
50                  if await request.is_disconnected():
51                      break
52                  data = await get_cached("dashboard")
53                  yield f"event: datastar-patch-signals\ndata: signals {data}\n"
54                  await asyncio.sleep(2.0)
55          except Exception:
56              pass
57      return StreamingResponse(stream(), media_type="text/event-stream",
58                               headers=make_headers())
```

Find the real bugs. Precision matters: reporting a non-bug as a bug counts against you.

Output format — output ONLY a numbered list, nothing else (no preamble, no fixes, no code):
Each entry on one line, exactly: `L<line>: <one-sentence description of the defect>`
Maximum 8 entries. If one line has two distinct defects, list them as separate entries with the same line number.