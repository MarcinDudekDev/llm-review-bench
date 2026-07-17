# v3 — command-generation, execution-scored

Model emits one shell command per task; harness runs it in a sandbox and
compares stdout to a golden value. Binary 1/0. No judge. See `spec.json`
for goldens + reference commands; `../../harness/exec_score.py` is the scorer.


## System prompt

> You are being evaluated on shell command accuracy. This is a pure ACCURACY test: think as long as you need, but you get exactly ONE shot per task with NO chance to run, test, or revise your commands. Each command will be executed once in a sandbox (macOS, /bin/bash, BSD userland: BSD sed/awk/sort/wc, plus python3 and jq available) in a directory containing the described input files, and its stdout will be compared byte-for-byte against the expected output (only a single trailing newline is trimmed). Correctness of the resulting stdout is ALL that matters. Speed does NOT matter — do not rush; reason carefully about edge cases, BSD-vs-GNU differences, exact formatting, and trailing whitespace before committing. Output EXACTLY 10 lines, one per task, each of the form `Qn: <command>` where <command> is the raw one-line shell command and nothing else. No explanations, no code fences, no backticks, no extra lines.


## Tasks


**Q1** — The file sales.csv contains exactly these 5 lines: 'item,qty' then 'red apple,3' then 'banana,-2' then 'dragon fruit,10' then 'cherry,7'. It is comma-separated with a header row; some item names contain spaces. Print the sum of the qty column (data rows only) as a single integer on one line.
  
_Trap:_ Default whitespace field-splitting in awk breaks on 'red apple,3' and 'dragon fruit,10' ($2 becomes 'apple,3' → 0), giving 5 instead of 18.

**Q2** — The file files.txt contains exactly these 5 lines in this order: patch-10.txt, patch-2.txt, patch-9.txt, patch-100.txt, patch-33.txt. Print all 5 lines sorted in ascending order by the NUMBER embedded after the dash (2, 9, 10, 33, 100), one filename per line.
  
_Trap:_ Plain `sort` is lexicographic: patch-10 and patch-100 land before patch-2, and patch-9 lands last.

**Q3** — The file colors.txt contains exactly these 8 lines in this order: red, blue, red, green, blue, red, yellow, green. Duplicates are NOT adjacent. Print the number of DISTINCT lines as a single integer with no leading or trailing whitespace.
  
_Trap:_ `uniq colors.txt | wc -l` fails twice: uniq only collapses ADJACENT duplicates (none are adjacent → 8), and BSD wc pads the number with leading spaces.

**Q4** — The file inventory.json contains a single-line JSON array: [{"name":"bolt","qty":120},{"name":"nut","qty":8},{"name":"washer","qty":30},{"name":"screw","qty":55}]. Print the name of every item whose qty is strictly greater than 25, one per line, in original array order, WITHOUT surrounding quotes.
  
_Trap:_ Forgetting jq's -r flag prints the names with double quotes around them.

**Q5** — The file log.txt contains exactly these 4 lines: 'error 404 at line 12', 'warn 5 issues', 'ok', 'error 500 at line 7'. Print the file with every maximal run of consecutive digits replaced by a single '#' character (so '404' becomes '#', not '###'). All other characters unchanged. This runs on macOS with BSD sed.
  
_Trap:_ GNU-style `sed 's/[0-9]\+/#/g'` on BSD sed treats \+ as a literal plus and silently changes NOTHING — output is the unmodified file.

**Q6** — The file steps.txt contains exactly these 7 lines in this order: one, two, three, four, five, six, seven. Print ONLY the second-to-last line of the file (a single line).
  
_Trap:_ Off-by-one in the tail/head combination prints 'seven' (last line) or 'five' instead of 'six'.

**Q7** — Two files, both UNSORTED. a.txt contains exactly these 4 lines: pear, apple, mango, kiwi. b.txt contains exactly these 4 lines: mango, banana, apple, plum. Print the lines that appear in BOTH files, one per line, sorted in ascending byte order.
  
_Trap:_ `comm -12 a.txt b.txt` on the unsorted files prints nothing (verified: empty stdout plus not-sorted warnings on stderr) because comm requires sorted input.

**Q8** — The file scores.txt contains exactly these 6 lines, one integer per line: 7, 3, 9, 12, 5, 10. Print the statistical MEDIAN of these 6 numbers. With an even count the median is the mean of the two middle values, so the correct output is a decimal number, printed exactly as Python's statistics.median would print it.
  
_Trap:_ Taking a single middle element of the sorted list gives 7 or 9; computing (7+9)//2 or printing an int gives 8 instead of 8.0.

**Q9** — The file users.txt contains exactly these 5 lines: 'alice:/bin/zsh', 'bob', 'carol:/bin/bash', 'dave:/bin/sh', 'eve'. Using ':' as the delimiter, print the SECOND field of every line that contains a delimiter, one per line, in file order. Lines WITHOUT a ':' (bob, eve) must produce NO output at all.
  
_Trap:_ `cut -d: -f2` without -s passes delimiter-less lines through whole, so 'bob' and 'eve' leak into the output.

**Q10** — The file notes.txt contains the three lines alpha, beta, gamma — but the file does NOT end with a trailing newline (the last line 'gamma' is unterminated; the file is exactly 16 bytes). Print the number of lines in the file, counting the final unterminated line, as a single integer with no leading or trailing whitespace. The correct answer is based on 3 lines of content.
  
_Trap:_ `wc -l` counts newline characters, giving 2 — and BSD wc additionally pads the number with leading spaces.
