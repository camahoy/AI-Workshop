"""Mixed-level group generation: bucket by level, shuffle within each
bucket, then round-robin across tables so no table ends up single-level."""
import random


def generate_groups(roster: list[dict], group_size: int) -> list[list[dict]]:
    if not roster:
        return []
    group_size = max(3, group_size)
    num_groups = max(1, -(-len(roster) // group_size))  # ceil division

    buckets: dict[str, list[dict]] = {}
    for person in roster:
        buckets.setdefault(person["level"], []).append(person)
    for bucket in buckets.values():
        random.shuffle(bucket)

    groups: list[list[dict]] = [[] for _ in range(num_groups)]
    cursor = 0
    for bucket in buckets.values():
        for person in bucket:
            groups[cursor % num_groups].append(person)
            cursor += 1
    return groups
