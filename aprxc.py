#!/usr/bin/env python
#
# Copyright © 2024 Fabian Neumann
# Licensed under the European Union Public Licence (EUPL).
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# SPDX-License-Identifier: EUPL-1.2

import argparse
import math
import sys
from collections import Counter
from collections.abc import Hashable, Iterable
from itertools import chain
from random import getrandbits
from textwrap import dedent
from typing import Self

__version__ = "1.1.2"


class ApproxiCount:
    """
    A class to estimate the number of distinct elements in an iterable.

    It uses the 'F0-Estimator' algorithm by S. Chakraborty, N. V. Vinodchandran
    and K. S. Meel, as described in their 2023 paper "Distinct Elements in
    Streams: An Algorithm for the (Text) Book"
    (https://arxiv.org/pdf/2301.10191#section.2).
    """

    def __init__(
        self,
        m: int = sys.maxsize,
        *,
        e: float = 0.1,
        d: float = 0.1,
        top: int = 0,
        cheat: bool = True,
        _debug: bool = False,
    ) -> None:

        self.n = min(m, int(math.ceil((12 / e**2) * math.log2((8 * m) / d))))
        self._round: int = 0
        self._total: int = 0
        self._memory: set[Hashable] = set()

        self.cheat = cheat
        self.top = top
        self._counters: Counter = Counter()

        self._debug = _debug
        self._mean_inacc = 0.0
        self._max_inacc = 0.0

    def count(self, item: Hashable) -> None:
        self._total += 1

        if getrandbits(self._round) == 0:
            self._memory.add(item)
            if self.top:
                self._counters[item] += 2**self._round
        else:
            self._memory.discard(item)

        if len(self._memory) == self.n:
            self._round += 1
            self._memory = {item for item in self._memory if getrandbits(1)}
            if self.top:
                self._counters = Counter(dict(self._counters.most_common(self.n)))

        if self._debug:
            self._print_debug()

    def _print_debug(self) -> None:
        inacc = abs((self._total - self.unique) / self._total)
        self._mean_inacc = (
            (self._mean_inacc * (self._total - 1)) + inacc
        ) / self._total
        self._max_inacc = max(self._max_inacc, inacc)
        if self._total % 50_000 == 0:
            sys.stdout.write(
                f"{self._total=} {self.unique=} {self._round=}"
                f" {self.n} {len(self._memory)=}"
                f" {inacc=:.2%} (mean: {self._mean_inacc:.3%} max: {self._max_inacc:.3%})"
                "\n"
            )

    @property
    def unique(self) -> int:
        # If `cheat` is True, we diverge slightly from the paper's algorithm:
        # normally it overestimates in 50%, and underestimates in 50% of cases.
        # But as we count the total number of items seen, we can use that as an
        # upper bound of possible unique values.
        result = int(len(self._memory) / (1 / 2 ** (self._round)))
        return min(self._total, result) if self.cheat else result

    def is_exact(self) -> bool:
        # During the first round, i.e. before the first random cleanup of our
        # memory set, our reported counts are exact.
        return self._round == 0

    def get_top(self) -> list[tuple[int, bytes]]:
        # EXPERIMENTAL
        return [(c, item) for item, c in self._counters.most_common(self.top)]

    @classmethod
    def from_iterable(cls, iterable: Iterable, /, **kw) -> Self:
        inst = cls(**kw)
        for x in iterable:
            if inst._debug and inst._total > 10_000_000:  # noqa: PLR2004
                inst._print_debug()
                break
            inst.count(x)
        return inst


Aprxc = ApproxiCount


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="aprxc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(
            """
            Estimate the number of distinct lines in a file or stream.

            Motivation:
            Easier to remember and always faster than `sort | uniq -c | wc -l`.
            Uses a fixed amount of memory for huge datasets, unlike the
            ever-growing footprint of `awk '!a[$0]++' | wc -l`.
            Counts accurately for the first ~83k unique values (on 64-bit
            systems), with a deviation of about 0.4-1% after that.
            """
        ),
    )
    parser.add_argument(
        "path",
        type=argparse.FileType("rb"),
        default=[sys.stdin.buffer],
        nargs="*",
        help="Input file path(s) and/or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--top",
        "-t",
        type=int,
        nargs="?",
        const=10,
        default=0,
        metavar="X",
        help="EXPERIMENTAL: Show X most common values. Off by default. If enabled, X defaults to 10.",
    )
    parser.add_argument(
        "--size",
        "-s",
        type=int,
        default=sys.maxsize,
        help="Total amount of data items, if known in advance. (Can be approximated.)",
    )
    parser.add_argument("--epsilon", "-E", type=float, default=0.1)
    parser.add_argument("--delta", "-D", type=float, default=0.1)
    parser.add_argument(
        "--cheat",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Use 'total seen' number as upper bound for unique count.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--debug", action="store_true")

    config = parser.parse_args()

    aprxc = ApproxiCount.from_iterable(
        chain.from_iterable(config.path),
        m=config.size,
        e=config.epsilon,
        d=config.delta,
        top=config.top,
        cheat=config.cheat,
        _debug=config.debug,
    )
    sys.stdout.write(
        " ".join(
            [
                str(aprxc.unique),
                (
                    ("(exact)" if aprxc.is_exact() else "(approximate)")
                    if config.verbose
                    else ""
                ),
            ]
        ).strip()
    )
    sys.stdout.write("\n")
    if config.top:
        sys.stdout.write(f"# {config.top} most common:\n")
        for count, value in aprxc.get_top():
            s: str = value.decode("utf-8", "backslashreplace")
            s = s.strip()
            sys.stdout.write(f"{count!s} {s}\n")


if __name__ == "__main__":
    run()
