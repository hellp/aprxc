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

In its default configuration (i.e. if the parameters `size`, `delta`, and
`epsilon` remain unchanged), `aprxc` uses a set data structure with 83187 slots,
meaning that until that number of unique elements are encountered the reported
counts are **exact**; only once this limit is reached 'the algorithm kicks in'
and numbers will become approximations.

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
