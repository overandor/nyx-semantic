"""Tests for cosine similarity and vector math."""

import math
from nyx.similarity import cosine_similarity, euclidean_distance


def test_identical_vectors():
    assert abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001


def test_orthogonal_vectors():
    assert abs(cosine_similarity([1, 0, 0], [0, 1, 0])) < 0.001


def test_opposite_vectors():
    assert abs(cosine_similarity([1, 0], [-1, 0]) - (-1.0)) < 0.001


def test_zero_vector():
    assert cosine_similarity([0, 0, 0], [1, 0, 0]) == 0.0


def test_different_lengths():
    assert cosine_similarity([1, 0], [1, 0, 0]) == 0.0


def test_empty_vectors():
    assert cosine_similarity([], []) == 0.0


def test_euclidean_basic():
    assert abs(euclidean_distance([0, 0], [3, 4]) - 5.0) < 0.001


def test_euclidean_same():
    assert euclidean_distance([1, 2, 3], [1, 2, 3]) == 0.0


def test_euclidean_different_lengths():
    assert euclidean_distance([1, 0], [1, 0, 0]) == float("inf")
