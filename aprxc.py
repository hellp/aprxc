#!/usr/bin/env python
from collections import Counter
from collections.abc import Hashable
from random import getrandbits
from typing import Self
import argparse
import math
import sys


class ApproxiCount:
    """
    A class to approximate the number of distinct values in a stream of elements
    using the 'F0-Estimator' algorithm by S. Chakraborty, N. V. Vinodchandran
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
    ):

        self.n = min(m, int(math.ceil((12 / e**2) * math.log((8 * m) / d, 2))))
        self._round: int = 0
        self._total: int = 0
        self._memory = set()

        self.cheat = cheat
        self.top = top
        self._counters = Counter()

        self._debug = _debug
        self._mean_inacc = 0.0
        self._max_inacc = 0.0

    def count(self, item: Hashable):
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

    def _print_debug(self):
        inacc = abs((self._total - self.unique) / self._total)
        self._mean_inacc = (
            (self._mean_inacc * (self._total - 1)) + inacc
        ) / self._total
        self._max_inacc = max(self._max_inacc, inacc)
        if self._total % 50_000 == 0:
            print(
                f"{self._total=} {self.unique=} {self._round=}"
                f" {self.n} {len(self._memory)=}"
                f" {inacc=:.2%} (mean: {self._mean_inacc:.3%} max: {self._max_inacc:.3%})"
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

    def get_top(self) -> list[(int, str)]:
        # EXPERIMENTAL
        return [(c, item) for item, c in self._counters.most_common(self.top)]

    @classmethod
    def from_iterable(cls, iterable, **kw) -> Self:
        inst = cls(**kw)
        for x in iterable:
            if inst._debug and inst._total > 10_000_000:
                break
            inst.count(x)
        return inst


Aprxc = ApproxiCount

parser = argparse.ArgumentParser(
    prog="aprxc",
    description="Get an *estimation* of distinct lines in a data stream.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument(
    "--top",
    "-t",
    type=int,
    default=0,
    help="EXPERIMENTAL: Show X most common values",
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


if __name__ == "__main__":
    aprxc = ApproxiCount.from_iterable(
        sys.stdin.buffer,
        m=config.size,
        e=config.epsilon,
        d=config.delta,
        top=config.top,
        cheat=config.cheat,
        _debug=config.debug,
    )
    print(
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
    if config.top:
        print(f"# {config.top} most common:")
        for count, item in aprxc.get_top():
            print(count, item.decode().rstrip())
