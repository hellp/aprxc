import subprocess

APRXY_ONLY = False
TIME_CMD = '/usr/bin/time --format="%M %e"'

PRE_PIPE = "cut -f 1 test-data/clickstream-enwiki-2024-04.tsv"
FILE = "-"

#PRE_PIPE = ""
#FILE = "test-data/clickstream-enwiki-2024-04.field1.txt"

# Create with
# `cat /dev/urandom | base64 -w 32 | head -n 10000000 > 10m_unique.txt`
# PRE_PIPE = ""
# FILE = "test-data/10m_unique.txt"

# PRE_PIPE = ""
# FILE = "test-data/linux-6.11.6.tar"



BEFORE_CMD = f"{PRE_PIPE} | {TIME_CMD}" if PRE_PIPE else TIME_CMD

cmds = [
    (
        "sort (default)",
        f"{BEFORE_CMD} sort {FILE} | uniq | wc -l",
    ),
    (
        "sort --parallel=16",
        f"{BEFORE_CMD} sort {FILE} --parallel=16 | uniq | wc -l",
    ),
    (
        "sort --parallel=1",
        f"{BEFORE_CMD} sort {FILE} --parallel=1 | uniq | wc -l",
    ),
    (
        "aprxc --epsilon=0.001",
        f"{BEFORE_CMD} uv run -q --no-project --python 3.13 aprxc.py {FILE} --epsilon=0.001",
    ),
    (
        "aprxc --epsilon=0.01",
        f"{BEFORE_CMD} uv run -q --no-project --python 3.13 aprxc.py {FILE} --epsilon=0.01",
    ),
    (
        "aprxc --epsilon=0.05",
        f"{BEFORE_CMD} uv run -q --no-project --python 3.13 aprxc.py {FILE} --epsilon=0.05",
    ),
    (
        "aprxc (py3.13)",
        f"{BEFORE_CMD} uv run -q --no-project --python 3.13 aprxc.py {FILE}",
    ),
    (
        "aprxc (py3.12)",
        f"{BEFORE_CMD} uv run -q --no-project --python 3.12 aprxc.py {FILE}",
    ),
    (
        "aprxc --epsilon=0.2",
        f"{BEFORE_CMD} uv run -q --no-project --python 3.13 aprxc.py {FILE} --epsilon=0.2",
    ),
    (
        "aprxc --epsilon=0.5",
        f"{BEFORE_CMD} uv run -q --no-project --python 3.13 aprxc.py {FILE} --epsilon=0.5",
    ),
    (
        "awk",
        f"{BEFORE_CMD} awk '!a[$0]++' {FILE} | wc -l",
    ),
]


for i, (name, cmd) in enumerate(cmds):
    if APRXY_ONLY and "aprxc" not in name and i > 0:  # always run the first
        continue
    output = subprocess.check_output(
        f"{cmd} >/dev/null",
        shell=True,
        stderr=subprocess.STDOUT,
    )
    mem, time = map(float, output.split())
    if i == 0:
        base_mem, base_time = mem, time
    max_name_len = max(len(c[0]) for c in cmds)
    print(
        f"{name:{max_name_len}} | {mem/1024:4.0f} ({mem/base_mem:4.0%}) | {time:4.1f} ({time/base_time:4.0%})"
    )
