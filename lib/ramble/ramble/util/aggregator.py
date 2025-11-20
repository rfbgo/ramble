# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import statistics
from enum import Enum
from typing import Any, Callable, List, Union
import csv
import io


class AggregatorType(Enum):
    """Defines the possible strategies for list aggregation."""

    LAST = "last"
    FIRST = "first"
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    CSV = "csv"


# TODO: should these be callable classes so they can hold .name?
def aggregate_last(data: list) -> object:
    return data[-1] if data else None


def aggregate_first(data: list) -> object:
    return data[0] if data else None


def aggregate_mean(data: list) -> float:
    # TODO: try using statistics.mean as an abtrirary callable
    return statistics.mean(data) if data else 0.0


def aggregate_min(data: list) -> object:
    return min(data) if data else None


def aggregate_max(data: list) -> object:
    return max(data) if data else None


def aggregator_csv(data: List[List[Any]]) -> str:  # <-- NEW
    """
    Aggregates a list of data rows (list of lists) into a single CSV-formatted string.
    """
    if not data:
        return ""

    # Use io.StringIO to treat a string as a file
    output = io.StringIO()
    # Create a CSV writer object
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write all rows to the in-memory buffer
    writer.writerows(data)

    # Get the resulting string and return it
    return output.getvalue()


AGGREGATOR_MAP: dict[AggregatorType, Callable[[list], object]] = {
    AggregatorType.LAST: aggregate_last,
    AggregatorType.FIRST: aggregate_first,
    AggregatorType.MEAN: aggregate_mean,
    AggregatorType.MIN: aggregate_min,
    AggregatorType.MAX: aggregate_max,
    AggregatorType.CSV: aggregator_csv,
}

# TODO: inline these type hints?
AggregatorCallable = Callable[[list], object]
AggregatorInput = Union[AggregatorType, AggregatorCallable]


def aggregator_factory(aggregator_input: AggregatorInput) -> AggregatorCallable:
    """
    Factory function to retrieve the aggregation callable (function or lambda).

    Args:
        aggregator_input: The AggregatorType enum or a custom callable function.

    Returns:
        A callable function that performs the list aggregation.
    """
    if isinstance(aggregator_input, AggregatorType):
        if aggregator_input not in AGGREGATOR_MAP:
            raise ValueError(f"Unknown predefined aggregation type: {aggregator_input}")
        return AGGREGATOR_MAP[aggregator_input]

    elif callable(aggregator_input):
        return aggregator_input

    else:
        raise TypeError(f"Invalid aggregator input type: {type(aggregator_input)}")
