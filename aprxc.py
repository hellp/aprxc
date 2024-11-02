#!/usr/bin/env python
#
# Copyright © 2024 Fabian Neumann
# Licensed under the European Union Public Licence (EUPL).
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# SPDX-License-Identifier: EUPL-1.2

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Hashable, Iterable
from itertools import chain
from random import getrandbits
from textwrap import dedent
from typing import Self

__version__ = "2.0.0"


class Aprxc:
    """
    A class to estimate the number of distinct values in an iterable.

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
        cheat: bool = False,
        count_total: bool = False,
        _debug: bool = False,
    ) -> None:

        self.n: int = min(m, int(math.ceil((12 / e**2) * math.log2((8 * m) / d))))
        self._round: int = 0
        self._memory: set[Hashable] = set()

        self.cheat = cheat
        self.top = top
        self._counters: Counter[Hashable] = Counter()

        self.count_total = count_total or cheat or _debug
        if self.count_total:
            self.total: int = 0
            self.count = self._count_with_total_and_debug

        self._debug = _debug
        if self._debug:
            self._curr_inacc = 0.0
            self._mean_inacc = 0.0
            self._max_inacc = 0.0

    def _optimized_count(self, item: Hashable) -> None:
        if getrandbits(self._round):  # `!= 0`, the more likely case first
            self._memory.discard(item)
        else:  # getrandbits(...) == 0
            self._memory.add(item)
            if self.top:
                self._counters[item] += 2**self._round

            # We can never reach the end of a round in the 'remove case' when
            # `getrandbit(...) != 0`, so it's safe to only check this here.
            if len(self._memory) == self.n:
                self._round += 1
                self._memory = {item for item in self._memory if getrandbits(1)}
                if self.top:
                    self._counters = Counter(dict(self._counters.most_common(self.n)))

    def _count_with_total_and_debug(self, item: Hashable) -> None:
        self._optimized_count(item)
        if self.count_total:
            self.total += 1
            if self._debug:  # implies _count_total
                self._calc_stats()

    count = _optimized_count

    @property
    def unique(self) -> int:
        # If `cheat` is True, we diverge slightly from the paper's algorithm:
        # normally it overestimates in 50%, and underestimates in 50% of cases.
        # But as we count the total number of items seen, we can use that as an
        # upper bound of possible unique values.
        result: int = int(len(self._memory) / (1 / 2 ** (self._round)))
        return min(self.total, result) if self.cheat else result

    def is_exact(self) -> bool:
        # During the first round, i.e. before the first random cleanup of our
        # memory set, our reported counts are exact.
        return self._round == 0

    def get_top(self) -> list[tuple[int, Hashable]]:
        # EXPERIMENTAL
        return [(c, item) for item, c in self._counters.most_common(self.top)]

    @classmethod
    def from_iterable(cls, iterable: Iterable, /, **kw) -> Self:
        inst = cls(**kw)
        for x in iterable:
            inst.count(x)
        return inst

    def _calc_stats(self) -> None:
        self._curr_inacc = abs((self.total - self.unique) / self.total)
        self._mean_inacc = (
            (self._mean_inacc * (self.total - 1)) + self._curr_inacc
        ) / self.total
        self._max_inacc = max(self._max_inacc, self._curr_inacc)

    def _debug_data(self) -> dict[str, float | int]:
        return {
            "inacc_curr": self._curr_inacc,
            "inacc_max": self._max_inacc,
            "inacc_mean": self._mean_inacc,
            "fill": len(self._memory),
            "n": self.n,
            "round": self._round,
            "total": self.total,
            "unique": self.unique,
        }

    def _print_debug(self) -> None:
        sys.stdout.write(
            json.dumps(
                {
                    k: format(v, ".3%") if k.startswith("inacc") else v
                    for k, v in self._debug_data().items()
                }
            )
            + "\n"
        )


def run() -> None:
    parser = argparse.ArgumentParser(
        prog="aprxc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(
            """
        Aproximately count the number of distinct lines in a file or pipe.

        Easier to remember, always faster and less memory-intensive (fixed upper
        bound!) than `sort | uniq | wc -l` or `awk '!a[$0]++' | wc -l`.

        In the default configuration results are precise until ~83k unique
        values (on 64-bit CPUs), with deviations of commonly 0.4-1% afterwards.
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
        help="Expected (estimated) total number of items. Reduces memory usages, increases inaccuracy.",
    )
    parser.add_argument("--epsilon", "-E", type=float, default=0.1)
    parser.add_argument("--delta", "-D", type=float, default=0.1)
    parser.add_argument(
        "--cheat",
        action="store_true",
        help="Improve accuracy by tracking 'total seen' and use it as upper bound for result. Implies --count-total.",
    )
    parser.add_argument(
        "--count-total",
        "-T",
        action="store_true",
        help="Count number of total seen values.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument(
        "--version", "-V", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Track, calculate, and display various internal statistics.",
    )

    config = parser.parse_args()

    aprxc: Aprxc = Aprxc.from_iterable(
        chain.from_iterable(config.path),
        m=config.size,
        e=config.epsilon,
        d=config.delta,
        top=config.top,
        cheat=config.cheat,
        count_total=config.count_total,
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

    if config.count_total:
        sys.stdout.write(
            "".join(["\n", "total: " if config.verbose else "", f"{aprxc._total}"])
        )
        sys.stdout.write(
            "".join(
                [
                    "\n",
                    "unique%:" if config.verbose else "",
                    f"{aprxc.unique/aprxc._total:.3%}",
                ]
            )
        )

    sys.stdout.write("\n")
    if config.top:
        sys.stdout.write(f"# {config.top} most common:\n")
        for count, value in aprxc.get_top():
            s: str = (
                value.decode("utf-8", "backslashreplace")
                if isinstance(value, bytes)
                else str(value)
            )
            s = s.strip()
            sys.stdout.write(f"{count!s} {s}\n")

    if config.debug:
        aprxc._print_debug()


if __name__ == "__main__":
    run()
