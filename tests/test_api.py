import pytest

import npg_porch_cli.api as porchApi


def test_addition():

    assert porchApi.add_two(1, 2) == 3
