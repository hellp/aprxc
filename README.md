# aprxc

A command-line tool (and Python class) to approximately count the number of
distinct elements in files (or a stream/pipe) using the “simple, intuitive,
sampling-based space-efficient algorithm” by S. Chakraborty, N. V. Vinodchandran
and K. S. Meel, as described in their 2023 paper [Distinct Elements in Streams:
An Algorithm for the (Text) Book](https://arxiv.org/pdf/2301.10191#section.2).

**Motivation:** Easier to remember, always faster and (much) less
memory-intensive than `sort | uniq | wc -l` or `awk '!a[$0]++' | wc -l`. In this
implementation’s default configuration results are precise until ~83k unique
values (on 64-bit CPUs), with deviations of commonly 0.4-1% afterwards.

## Installation

Choose your preferred way to install it from [PyPI](https://pypi.org/project/aprxc/):

```shell
pip install aprxc
uv tool install aprxc
```

Alternatively, run it in an isolated environment, using [pipx
run](https://pipx.pypa.io/) or [uvx](https://docs.astral.sh/uv/concepts/tools/):

```shell
pipx run aprxc --help
uvx aprxc --help
```

Lastly, as `aprxc.py` has no dependencies besides Python 3.11+, you can simply
download the script, run it, put it your PATH, vendor it, etc.

## Features and shortcomings

* Easier to remember than the pipe constructs.
* 20–60% faster than sort/uniq.
* 30–99% less memory-intensive than sort/uniq (for mid/high-cardinality data)
* (Roughly double these numbers when compared against awk.)
* Memory usage has a (configurable) upper bound.

Now let's address the elephant in the room: These advantages are bought with
**an inaccuracy in the reported results**. But how inaccurate?

### About inaccuracy

In its default configuration the algorithm has a **mean inaccuracy of about
0.4%**, with **outliers around 1%**. For example, if the script encounters 10M
(`10_000_000`) actual unique values, the reported count is typically ~40k off
(e.g. `10_038_680`), sometimes ~100k (e.g. `9_897_071`).

**However:** If the number of encountered actual unique elements is smaller than
the size of the internally used set data structure, then the reported counts are
**exact**; only once this limit is reached, the approximation algorithm 'kicks
in' and the result will become an approximation.

Here's an overview (highly unscientific!) of how the algorithm parameters 𝜀 and
𝛿 (`--epsilon` and `--delta` on the command line) affect the inaccuracy. The
default of `0.1` for both values seems to strike a good balance (and a memorable
inaccuracy of ~1%). Epsilon is the 'main manipulation knob', and you can see
quite good how its value affects especially the maximum inaccuracy.

For this first table I counted 10 million unique 32-character strings, and for
each iteration checked the reported count and compared to the actual number of
unique items. _Mean inacc._ is the mean inaccuracy across all 10M steps; _max
inacc._ is the highest deviation encountered; _memory usage_ is the linux tool
`time`'s reported _maxresident_; _time usage_ is wall time.

| tool (w/ options)     | memory [MiB]|    time [s]|mean ina.| max ina.|   set size|
|-----------------------|------------:|-----------:|--------:|--------:|----------:|
|`sort \| uniq \| wc -l`| 1541 (100%) |  5.5 (100%)|      0% |      0% |          —|
|`sort --parallel=16`   | 1848 (120%) |  5.2 ( 95%)|      0% |      0% |          —|
|`sort --parallel=1`    |  780 ( 51%) | 18.1 (328%)|      0% |      0% |          —|
|`aprxc --epsilon=0.001`| 1044 ( 68%) |  4.1 ( 75%)|      0% |      0% |831_863_138|
|`aprxc --epsilon=0.01` | 1137 ( 74%) |  5.5 (100%)|  0.001% |   0.02% |  8_318_632|
|`aprxc --epsilon=0.05` |   78 (  5%) |  2.2 ( 40%)|  0.080% |   0.42% |    332_746|
|`aprxc` (Python 3.13)  |   35 (  2%) |  1.8 ( 32%)|  0.400% |   1.00% |     83_187|
|`aprxc` (Python 3.12)  |   28 (  2%) |  2.0 ( 36%)|  0.400% |   1.00% |     83_187|
|`aprxc --epsilon=0.2`  |   26 (  2%) |  1.8 ( 32%)|  0.700% |   2.10% |     20_797|
|`aprxc --epsilon=0.5`  |   23 (  1%) |  1.7 ( 31%)|  1.700% |   5.40% |      3_216|
|`awk '!a[$0]++'\|wc -l`| 3094 (201%) |  9.3 (169%)|      0% |      0% |          —|


#### Other time/memory consumption benchmarks

For `linux-6.11.6.tar`, a medium-cardinality (total: 39_361_138, 43.3% unique)
input file:

| tool (w/ options)     | memory [MiB]|    time [s]|
|-----------------------|------------:|-----------:|
|`sort \| uniq \| wc -l`| 6277 (100%) | 41.4 (100%)|
|`sort --parallel=16`   | 7477 (119%) | 36.7 ( 89%)|
|`sort --parallel=1`    | 3275 ( 52%) |158.6 (383%)|
|`aprxc --epsilon=0.001`| 2081 ( 33%) | 13.1 ( 32%)|
|`aprxc --epsilon=0.01` | 1364 ( 22%) | 15.3 ( 37%)|
|`aprxc --epsilon=0.05` |  105 (  2%) |  8.2 ( 20%)|
|`aprxc` (Python 3.13)  |   39 (  1%) |  7.2 ( 17%)|
|`aprxc` (Python 3.12)  |   35 (  1%) |  8.1 ( 20%)|
|`aprxc --epsilon=0.2`  |   27 (  0%) |  7.2 ( 17%)|
|`aprxc --epsilon=0.5`  |   23 (  0%) |  7.2 ( 17%)|
|`awk '!a[$0]++'\|wc -l`| 5638 ( 90%) | 24.8 ( 60%)|

For `cut -f 1 clickstream-enwiki-2024-04.tsv`, a low-cardinality (total:
34_399_603, unique: 6.4%), once via temporary file¹, once via pipe²:

| tool (w/ options)     |   ¹mem [MiB]|   ¹time [s]|   ²mem [MiB]|   ²time [s]|
|-----------------------|------------:|-----------:|------------:|-----------:|
|`sort \| uniq \| wc -l`| 4823 (100%) | 11.6 (100%)|   14 (100%) | 50.3 (100%)|
|`sort --parallel=16`   | 5871 (122%) | 11.9 (103%)|   14 (100%) | 48.7 ( 97%)|
|`sort --parallel=1`    | 2198 ( 46%) | 50.5 (436%)|   10 ( 71%) | 48.7 ( 97%)|
|`aprxc --epsilon=0.001`|  214 (  4%) | 10.8 ( 93%)|  215 (1532%)| 10.7 ( 21%)|
|`aprxc --epsilon=0.01` |  215 (  4%) | 10.5 ( 91%)|  215 (1534%)| 10.6 ( 21%)|
|`aprxc --epsilon=0.05` |   73 (  2%) |  8.2 ( 71%)|   73 (524%) |  7.7 ( 15%)|
|`aprxc` (Python 3.13)  |   35 (  1%) |  6.4 ( 55%)|   36 (254%) |  6.5 ( 13%)|
|`aprxc` (Python 3.12)  |   29 (  1%) |  7.4 ( 64%)|   29 (204%) |  7.2 ( 14%)|
|`aprxc --epsilon=0.2`  |   27 (  1%) |  5.8 ( 50%)|   27 (189%) |  5.8 ( 11%)|
|`aprxc --epsilon=0.5`  |   23 (  0%) |  6.0 ( 52%)|   23 (164%) |  6.1 ( 12%)|
|`awk '!a[$0]++'\|wc -l`|  666 ( 14%) | 15.7 (136%)|  666 (4748%)| 14.4 ( 29%)|

### Is it useful?

You have to accept the inaccuracies, obviously. But if you are working
exploratory and don't care about exact number or plan to round or throw them
away anyway; or if or you are in a memory-constrained situation and need to deal
with large input files or streaming data; or if you just cannot remember the
multi-command pipe alternatives, then this might be a tool for you.

### The experimental 'top most common' feature

I've added a couple of lines of code to support a 'top most common' items
feature. An alternative to the `sort | uniq -c | sort -rn | head`-pipeline or
[Tim Bray's nice `topfew` tool (written in
Go)](https://github.com/timbray/topfew/).

It kinda works, but…

- The counts are good, even surprisingly good, as for the whole base algorithm,
  but definitely worse and not as reliable as the nice 1%-mean-inaccuracy for
  the total count case.
- I lack the mathematical expertise to prove or disprove anything about that
  feature.
- If you ask for a top 10 (`-t10` or `--top 10`), you mostly get what you
  expect, but if the counts are close the lower ranks become 'unstable'; even
  rank 1 and 2 sometimes switch places etc.
- Compared with `topfew` (I wondered if this approximation algorithm could be
  _an optional_ flag for `topfew`), this Python code is impressively close to
  the Go performance, especially if reading a lot of data from a pipe.
  Unfortunately, I fear that this algorithm is not parallelizable. But I leave
  that, and the re-implementation in Go or Rust, as an exercise for the reader
  :)
- Just try it!

## Command-line interface

```shell
usage: aprxc [-h] [--top [X]] [--size SIZE] [--epsilon EPSILON]
             [--delta DELTA] [--cheat] [--count-total] [--verbose] [--version]
             [--debug]
             [path ...]

Aproximately count the number of distinct lines in a file or pipe.

positional arguments:
  path                  Input file path(s) and/or '-' for stdin (default:
                        stdin)

options:
  -h, --help            show this help message and exit
  --top [X], -t [X]     EXPERIMENTAL: Show X most common values. Off by
                        default. If enabled, X defaults to 10.
  --size SIZE, -s SIZE  Expected (estimated) total number of items. Reduces
                        memory usages, increases inaccuracy.
  --epsilon EPSILON, -E EPSILON
  --delta DELTA, -D DELTA
  --cheat               Improve accuracy by tracking 'total seen' and use it
                        as upper bound for result.
  --count-total, -T     Count number of total seen values.
  --verbose, -v
  --version, -V         show program's version number and exit
  --debug               Track, calculate, and display various internal
                        statistics.
usage: aprxc [-h] [--top [X]] [--size SIZE] [--epsilon EPSILON]
             [--delta DELTA] [--cheat] [--verbose] [--version] [--benchmark]
             [--debug] [--debug-lines N]
             [path ...]
