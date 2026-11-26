import pytest

from cardarena_tournament_core.pairings._bracket import bracket_size, seed_positions


def test_seed_positions_small_brackets():
    assert seed_positions(2) == [1, 2]
    assert seed_positions(4) == [1, 4, 2, 3]
    assert seed_positions(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_seed_positions_16_contains_every_seed_once():
    assert sorted(seed_positions(16)) == list(range(1, 17))
    assert seed_positions(16)[:4] == [1, 16, 8, 9]


def test_seed_positions_top_two_seeds_are_in_opposite_halves():
    positions = seed_positions(32)

    assert positions.index(1) < 16 <= positions.index(2)


@pytest.mark.parametrize(
    "n,size", [(1, 2), (2, 2), (3, 4), (4, 4), (5, 8), (8, 8), (9, 16), (33, 64)]
)
def test_bracket_size(n: int, size: int):
    assert bracket_size(n) == size
