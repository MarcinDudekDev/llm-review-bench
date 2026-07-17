You are reviewing code for a stack pinned to exact versions: **Python 3.14 / FastAPI (Starlette 0.50) / Datastar 1.0**, **PHP 8.3+ / WordPress 6.x**, **zsh 5.9 on macOS 15 (stock BSD userland)**. Line numbers are given; refer to them exactly.

Report ONLY defects that cause incorrect behavior, an error, or a broken wire protocol **on these exact versions**. Style, robustness, hardening, performance, and "best practice" suggestions are NOT findings and will be penalized. Maximum 12 findings.

**PART A — Python 3.14, FastAPI app (served by uvicorn), Datastar 1.0 client on the page**
```
 1  import asyncio
 2  import json
 3  import time
 4  from fastapi import FastAPI, Request
 5  from fastapi.responses import StreamingResponse
 6
 7  app = FastAPI()
 8  loop = asyncio.get_event_loop()
 9  METRICS: dict[str, int] = {"ticks": 0}
10
11  def csv_rows():
12      yield "id,name\n"
13      for i in range(3):
14          time.sleep(0.1)
15          yield f"{i},row{i}\n"
16
17  @app.get("/export")
18  def export():
19      return StreamingResponse(csv_rows(), media_type="text/csv")
20
21  def render_card(item: dict) -> str:
22      return f"<article id='card-{item["id"]}'>\n  <b>{item["name"]}</b>\n</article>"
23
24  async def fetch(key: str) -> str:
25      if not key:
26          raise ValueError("empty key")
27      await asyncio.sleep(0.01)
28      return key.upper()
29
30  async def card_stream(request: Request):
31      while not await request.is_disconnected():
32          METRICS["ticks"] += 1
33          item = {"id": METRICS["ticks"], "name": f"tick {METRICS['ticks']}"}
34          html = render_card(item)
35          yield "event: datastar-merge-fragments\n"
36          yield f"data: fragments {html}\n\n"
37          yield ": keepalive\n\n"
38          await asyncio.sleep(1.0)
39
40  @app.get("/stream")
41  async def stream(request: Request):
42      return StreamingResponse(card_stream(request), media_type="text/event-stream")
43
44  async def warm_cache(keys: list[str]) -> None:
45      try:
46          async with asyncio.TaskGroup() as tg:
47              for k in keys:
48                  tg.create_task(fetch(k))
49      except ValueError:
50          METRICS["ticks"] = 0
```

**PART B — PHP 8.3, WordPress plugin excerpt (WP APIs behave per official docs)**
```
 1  <?php
 2  const MWF_ALLOWED = ['draft', 'publish', 'pending'];
 3
 4  function mwf_render_badge(int $score): string {
 5      $label = $score > 80 ? 'fast' : $score > 50 ? 'ok' : 'slow';
 6      return '<span class="badge">' . esc_html($label) . '</span>';
 7  }
 8
 9  function mwf_settings(array $user_args): array {
10      $defaults = ['per_page' => 10, 'order' => 'desc', 'cache' => true];
11      return $defaults + $user_args;
12  }
13
14  function mwf_handle_save() {
15      $nonce = $_POST['_mwf_nonce'] ?? '';
16      if (wp_verify_nonce($nonce, 'mwf_save') === true) {
17          update_option('mwf_settings', mwf_settings($_POST));
18      } else {
19          wp_die('Bad nonce', 403);
20      }
21  }
22
23  function mwf_filter_posts(array $posts): array {
24      $status = $_GET['status'] ?? 'publish';
25      $keep = array_filter($posts, fn($p) => $p->post_status === $status
26          && in_array($p->post_status, MWF_ALLOWED));
27      usort($keep, fn($a, $b) => $a->menu_order > $b->menu_order);
28      return array_values($keep);
29  }
```

**PART C — zsh 5.9 script on macOS 15 (stock /bin/date, no coreutils)**
```
 1  #!/bin/zsh
 2  # precondition: at least one debug*.log exists
 3  set -e
 4  backup_dir="$HOME/backups"
 5  files=(~/Sites/wp-content/debug*.log)
 6  first=$files[0]
 7  stamp=$(date -d '-1 day' '+%Y%m%d')
 8  dest="$backup_dir/wp $stamp"
 9  mkdir -p $dest
10  cp $first $dest/
11  echo "backed up $first -> $dest"
```

**PART D — Predict the EXACT stdout of this program on Python 3.14 (it is deterministic):**
```
import asyncio

async def quick(tag):
    print(f"Q{tag}")
    return tag

async def slow(tag):
    print(f"S{tag}-in")
    await asyncio.sleep(0)
    print(f"S{tag}-out")
    return tag

async def main():
    t1 = asyncio.create_task(slow(1))
    t1.add_done_callback(lambda _: print("CB1"))
    t2 = asyncio.create_task(slow(2))
    t2.cancel()
    print("M1")
    await quick(3)
    print("M2")
    await asyncio.sleep(0)
    print("M3")
    try:
        await t2
    except asyncio.CancelledError:
        print("C2")
    print("M4", t1.done())
    await t1
    print("M5")

asyncio.run(main())
```

**ANSWER IN EXACTLY THIS FORMAT (nothing else):**
```
FINDINGS:
<Part-letter>:<line> — <mechanism, max 15 words>
(one per line, sorted by part letter then line number; write "none" if no defects)
OUTPUT:
<the exact stdout of Part D, every line verbatim>
```