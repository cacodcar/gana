"""Generate a reproducible chart gallery from illustrative numerical inputs."""

import argparse
from pathlib import Path

from gana import I, P, Prg
from gana.plotting import grid


def gallery():
    """Compare profiles, contributions, observations and supplied intervals."""
    p = Prg()
    p.time = I(size=6)
    p.solar = P(p.time, _=[0, 2, 5, 6, 3, 0])
    p.wind = P(p.time, _=[3, 2, 1, 2, 3, 4])
    p.demand = P(p.time, _=[3, 4, 6, 8, 6, 4])
    p.observed = P(p.time, _=[2.8, 4.2, 5.8, 8.1, 6.2, 3.9])
    profiles = p.line(p.solar, p.wind, title="Profiles")
    grouped = p.bar(p.solar, p.wind, title="Grouped bars")
    dispatch = (p.stacked(p.solar, p.wind) + p.demand.line()).with_options(
        title="Stacked bars and demand",
    )
    interval = (
        p.demand.band(
            lower=[2, 3, 5, 7, 5, 3],
            upper=[4, 5, 7, 9, 7, 5],
        )
        + p.demand.line()
        + p.observed.scatter()
    )
    interval = interval.with_options(title="Bounds and observations")
    errors = p.observed.errorbar(yerr=0.4, title="Observation intervals")
    areas = p.area(p.solar, p.wind, kind="stacked", title="Stacked areas")
    return grid([[profiles, grouped], [dispatch, interval], [errors, areas]])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    gallery().save(args.output, fig_size=(10, 9), profile="print")
