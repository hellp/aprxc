# ApproxyCount (`aprxc`)

A Python script/class to approximate the number of distinct values in a stream
of elements using the *F0-Estimator* algorithm by S. Chakraborty, N. V.
Vinodchandran and K. S. Meel, as described in their 2023 paper "Distinct
Elements in Streams: An Algorithm for the (Text) Book"
(https://arxiv.org/pdf/2301.10191#section.2).

It is similar to what the command line pipelines `sort | uniq -c | wc -l`, or
alternatively `awk '!a[$0]++' | wc -l`, do.

Compared to sort/uniq:

- sort/uniq always uses less memory (about 30-50%).
- sort/uniq is about 5 times *slower*.

Compared to 'the awk construct':

- awk uses about the same amount of time (0.5x-2x).
- awk uses *much more* memory for large files. Basically linear to the file
    size, while ApproxiCount has an upper bound. For typical multi-GiB files
    this can mean factors of 20x-150x, e.g. 5GiB (awk) vs. 40MiB (aprxc).

Now let's address the elephant in the room: All these advantages (yes, the pro
and cons are pretty balanced, but overall one can say that `aprxc` performs
generally better than the alternatives, especially with large data inputs) are
bought with **an inaccuracy in the reported counts**.

## About inaccuracy

But how inaccurate? In it's default configuration you'll get a **mean inaccuracy
of about 0,4%**, with occasional **outliers around 1%**. For example, if the
script encounters 10M (`10_000_000`) actual unique values, the reported count is
typically ~40k off (e.g. `10_038_680`), sometimes ~100k (e.g. `9_897_071`).

Here's an overview (highly unscientific!) of how the algorithm parameters 𝜀 and
𝛿 (`--epsilon` and `--delta` on the command line) affect the inaccuracy. The
defaults of `0.1` for both values seem to strike a good balance (and a memorable
inaccuracy of ~1%). Epsilon is the 'main manipulation knob', and you can see
quite good how its value affects especially the maximum inaccuracy.

(For this overview I counted 10 million unique 32-character strings, and _for
each_ iteration I checked the reported count and compared to the actual number
of unique items. 'Mean inacc.' is the mean inaccuracy across all 10M steps;
'max inacc.' is the highest off encountered; memory usage is the linux tool
`time`'s reported 'maxresident'; time usage is wall time.)

|   𝜀  |  𝛿  | set size | mean inacc. | max inacc.  |   memory usage  |  time usage  |
| ---- | --- | -------- | ----------- | ----------- | --------------- | ------------ |
| 0.01 | 0.1 |  8318632 |     0.004%  |     0.034%  | 1155MiB (4418%) | 12.5s (162%) |
| 0.05 | 0.1 |   332746 |     0.17%   |     0.43%   |   70MiB  (269%) |  9.5s (123%) |
| 0.1  | 0.1 |    83187 |   __0.37%__ |   __0.97%__ |   26MiB  (100%) |  7.7s (100%) |
| 0.2  | 0.1 |    20797 |     0.68%   |     2.16%   |   17MiB   (65%) |  7.3s  (95%) |
| 0.5  | 0.5 |     3216 |     1.75%   |     5.45%   |   13MiB   (36%) |  8.8s (114%) |

**Important (and nice feature):** In its default configuration, the algorithm
uses a set data structure with 83187 slots, meaning that until that number of
unique elements are encountered the reported counts are **exact**; only once
this limit is reached, the 'actual' approximation algorithm kicks in and numbers
will become estimations.

## Is it useful?

- You have to be okay with the inaccuracies, obviously.
- However, for small unique counts (less than 80k) the numbers are correct and
  the command might be easier to remember than the sort/uniq pipe or the awkward
  awk construct.
- It's basically always faster than the sort/uniq pipe.
- If you are memory-constrained and want to deal with large files, it might be
  an option.
- If you are working exploratory and don't care about exact numbers or you will
  round them anyway in the end, this can save you time.

## The experimental 'top most common' feature

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

## Command-line interface:

```shell
usage: aprxc [-h] [--top TOP] [--size SIZE] [--delta DELTA] [--epsilon EPSILON] [--verbose]

Get an *estimation* of distinct lines in a data stream.

options:
  -h, --help            show this help message and exit
  --size SIZE, -s SIZE  Total amount of data items, if known in advance. (Can be approximated.) (default: 9223372036854775807)
  --delta DELTA, -D DELTA
  --epsilon EPSILON, -E EPSILON
  --top TOP, -t TOP     EXPERIMENTAL: Show X most common values (default: 0)
  --verbose, -v
```
