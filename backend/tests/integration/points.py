"""A plain coordinate for the integration tests that measure distances with app.real_cafes.distance_m."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float
