# v4 — adversarially-filtered hard command generation

18 validated hard shell-command tasks (Fable Q1-Q10 + Grok G1-G8), same
execution-scoring as v3. Built to separate frontier models where v3 tied at ceiling.


## Method: strong models as difficulty oracles

"Make it hard" prompting produced a 10/10 ceiling twice (v3). v4 instead uses an
**adversarial filter**: Fable and Grok each propose candidates, every reference
command is validated against its golden by execution, then each model attempts the
*other's* tasks one-shot. A task the opposing strong model fails is empirically hard.


**Filter outcome: 17/18 candidate cross-attempts were SOLVED.** Only one task
(Fable's Q5) stumped the opposing strong model (Grok) — and Q5 hinges on this host's
libm `%.2f` half-way rounding, which is unknowable without executing it, so it's a
platform gotcha more than a reasoning discriminator.


**Finding: one-shot BSD shell-command generation is saturated for frontier models.**
Two capable proposers could not reliably author a shell task that a frontier peer fails.
So v4 runs the full validated set (not just the 1 survivor) against the contenders.


## Tasks


**Q1** (fable-5) — The file sales.csv contains exactly these 6 lines:
  
_Trap:_ fruit and dairy tie at exactly 16.30; `sort -k2,2nr` (or -rn) without an explicit `-k1,1` secondary key leaves the tie order to sort's last-resort whole-line comparison, which under -r puts fruit befo

**Q2** (fable-5) — Two files. products.csv contains exactly these 4 lines (NOT sorted):
  
_Trap:_ join requires both inputs pre-sorted on the key — products.csv is not, so a bare `join products.csv stock.csv` silently drops/garbles rows. And `-e NA` only substitutes for missing fields when an expl

**Q3** (fable-5) — The file words.txt has DOS (CRLF) line endings and contains exactly these 7 lines: Apple, BANANA, apple, Cherry, banana, CHERRY, date (each line terminated by \r\n). Print the lines deduplicated CASE-INSENSITIVELY, keeping only the FIRST occurrence of each word in its original spelling and original order. Output must use plain LF line endings with no carriage returns.
  
_Trap:_ Forgetting to strip \r yields output whose every line ends in an invisible CR — dedup still works but the byte compare fails. Alternatively `sort -uf` dedups case-insensitively but destroys original o

**Q4** (fable-5) — The file stats.txt contains exactly these 4 lines:
  
_Trap:_ The natural `printf "%.0f"` uses IEEE round-half-to-even: 5/2=2.5 prints as 2, not the required 3 (verified: BSD awk %.0f of 2.5 -> 2). python3's round() has the same banker's-rounding behavior. You m

**Q5** (fable-5) — The file ledger.txt contains exactly these 6 lines:
  
_Trap:_ The balance goes negative mid-stream: %09.2f puts the zeros AFTER the minus sign (-00019.45, 9 chars total). Hand-rolling the padding, using width 8, or space-padding gives a near-miss. Forgetting to 

**Q6** (fable-5) — The file matrix.tsv is TAB-separated with exactly these 3 rows and 3 columns:
  
_Trap:_ awk's default FS splits on ANY whitespace, so `blue pen` becomes two fields and the transpose gains a phantom column — you must set FS to a literal tab (and join output cells with tabs, not OFS-defaul

**Q7** (fable-5) — The file scores.txt contains exactly these 7 lines:
  
_Trap:_ Three stacked decisions: bob's max is his SECOND entry (92, not 85 — first-occurrence dedup like `sort -u -k1,1` or `!seen[$1]++` keeps 85); bob/dave tie at 92 and alice/eve tie at 90, so without an e

**Q8** (fable-5) — The file events.txt contains exactly these 5 lines:
  
_Trap:_ GNU `date -d '03-Mar-2024'` does not exist on BSD; BSD needs `date -j -f`, and reaching for the date binary at all invites locale/clock issues — the robust answer is a month-name lookup table in awk. 

**Q9** (fable-5) — The file access.log contains exactly these 7 lines:
  
_Trap:_ grep -P and \d do not exist in BSD grep (must use -E with [0-9] classes). Leaving `uniq -c` output as-is fails on its leading space padding and count-first order — it must be reswizzled to `ip count`.

**Q10** (fable-5) — The file orders.json contains exactly this JSON (one line):
  
_Trap:_ Doing the formatting inside jq is the killer: jq prints 10.00*1 as `10` (not `10.00`) and float sums can surface as 14.649999999999999; jq has no printf-style %.2f, and the `*100|round/100` idiom stil

**G1** (grok) — You are given two CSV files in the current directory (headers on line 1):
  
_Trap:_ Missing UNKNOWN for orphan SKUs; sorting REVENUE lexicographically; forgetting qty*price; including categories with zero sales.

**G2** (grok) — File m.csv is a comma-separated table with a header. Lines may end with CRLF (\r\n). Columns: host,cpu,mem. The mem field may be empty.
  
_Trap:_ Leaving CR in fields; empty mem not coerced to 0; cpu as %.2f; natural sort so web2 before web10; treating 9.50 filter as string.

**G3** (grok) — File scores.csv has header team,user,score and one row per user score (integers).
  
_Trap:_ Wrong %.2f rounding for 26/3; including n<2 teams; sort key order AVG/N/TEAM wrong; integer division.

**G4** (grok) — File app.log has lines: DATE LEVEL where LEVEL is a lowercase word (error/info/warn/...).
  
_Trap:_ Emitting uniq -c leading spaces as final format; forgetting toupper; zero-pad width wrong; sorting by level before count.

**G5** (grok) — Two parallel files (same number of lines, no headers):
  
_Trap:_ Comparing length to need as strings; swapping L/FREQ columns; using uniq -c padding as output; sorting L before FREQ.

**G6** (grok) — File data.json is a single JSON object:
  
_Trap:_ Spaces after commas in names; unsorted names; counting tag occurrences not users; including Dee empty tags; wrong secondary sort.

**G7** (grok) — Two headerless CSV files:
  
_Trap:_ Coercing ids to numbers so 01==1; join without sort dropping rows; keeping unmatched id 3; wrong field after join.

**G8** (grok) — File text.txt contains English prose (may include punctuation and mixed case).
  
_Trap:_ Keeping short words; failing to lowercase; punctuation glued to words; not zero-padding; wrong top-5 tie-break order.
