"""A registry of deterministic transforms and a small tracked ML pipeline.

A transform is a pure, deterministic function from an ordered list of input values
and a parameter dictionary to an ordered list of output values. Because transforms
are deterministic, a run can be re-executed to verify that the recorded outputs are
reproduced bit for bit. The demonstration transforms implement a tiny but complete
pipeline: standardize a dataset, fit a ridge-regression model by closed form, and
evaluate it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

Transform = Callable[[list[Any], dict[str, Any]], list[Any]]

_REGISTRY: dict[str, Transform] = {}


def register(name: str) -> Callable[[Transform], Transform]:
    def decorator(function: Transform) -> Transform:
        _REGISTRY[name] = function
        return function

    return decorator


def get_transform(name: str) -> Transform:
    if name not in _REGISTRY:
        raise KeyError(f"unknown transform {name}")
    return _REGISTRY[name]


def _column_stats(rows: list[list[float]]) -> tuple[list[float], list[float]]:
    columns = len(rows[0])
    means = [0.0] * columns
    for row in rows:
        for index, value in enumerate(row):
            means[index] += value
    means = [total / len(rows) for total in means]
    variances = [0.0] * columns
    for row in rows:
        for index, value in enumerate(row):
            variances[index] += (value - means[index]) ** 2
    stds = [max((total / len(rows)) ** 0.5, 1e-9) for total in variances]
    return means, stds


@register("standardize")
def _standardize(inputs: list[Any], params: dict[str, Any]) -> list[Any]:
    dataset = inputs[0]
    rows = [list(map(float, row)) for row in dataset["features"]]
    means, stds = _column_stats(rows)
    standardized = [
        [round((value - means[index]) / stds[index], 9) for index, value in enumerate(row)]
        for row in rows
    ]
    return [{"features": standardized, "labels": list(dataset["labels"])}]


def _solve_ridge(
    rows: list[list[float]], labels: list[float], l2: float
) -> tuple[list[float], float]:
    columns = len(rows[0])
    design = [[1.0, *row] for row in rows]
    width = columns + 1
    ata = [[0.0] * width for _ in range(width)]
    atb = [0.0] * width
    for row, label in zip(design, labels, strict=True):
        for i in range(width):
            atb[i] += row[i] * label
            for j in range(width):
                ata[i][j] += row[i] * row[j]
    for i in range(1, width):
        ata[i][i] += l2
    solution = _gaussian_solve(ata, atb)
    return solution[1:], solution[0]


def _gaussian_solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [[*row[:], vector[index]] for index, row in enumerate(matrix)]
    for pivot in range(size):
        best = max(range(pivot, size), key=lambda r: abs(augmented[r][pivot]))
        augmented[pivot], augmented[best] = augmented[best], augmented[pivot]
        divisor = augmented[pivot][pivot] or 1e-12
        for column in range(pivot, size + 1):
            augmented[pivot][column] /= divisor
        for row in range(size):
            if row != pivot:
                factor = augmented[row][pivot]
                for column in range(pivot, size + 1):
                    augmented[row][column] -= factor * augmented[pivot][column]
    return [augmented[row][size] for row in range(size)]


@register("train_ridge")
def _train_ridge(inputs: list[Any], params: dict[str, Any]) -> list[Any]:
    dataset, config = inputs[0], inputs[1]
    l2 = float(config.get("l2", 1.0))
    rows = [list(map(float, row)) for row in dataset["features"]]
    labels = [float(value) for value in dataset["labels"]]
    weights, bias = _solve_ridge(rows, labels, l2)
    return [
        {
            "weights": [round(weight, 9) for weight in weights],
            "bias": round(bias, 9),
            "l2": l2,
        }
    ]


@register("evaluate")
def _evaluate(inputs: list[Any], params: dict[str, Any]) -> list[Any]:
    model, dataset = inputs[0], inputs[1]
    rows = [list(map(float, row)) for row in dataset["features"]]
    labels = [float(value) for value in dataset["labels"]]
    weights = model["weights"]
    bias = model["bias"]
    predictions = [bias + sum(w * x for w, x in zip(weights, row, strict=True)) for row in rows]
    mean_label = sum(labels) / len(labels)
    sse = sum(
        (prediction - label) ** 2 for prediction, label in zip(predictions, labels, strict=True)
    )
    sst = sum((label - mean_label) ** 2 for label in labels) or 1e-12
    return [{"mse": round(sse / len(labels), 9), "r2": round(1.0 - sse / sst, 9)}]
