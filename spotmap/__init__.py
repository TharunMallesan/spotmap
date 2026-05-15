"""spotmap — Interactive epidemiological spot maps for India."""

from .exceptions import ColumnNotFoundError, NoCasePointsError, SpotMapError
from .map_builder import SpotMap

__version__ = "0.1.0"
__all__ = ["SpotMap", "SpotMapError", "ColumnNotFoundError", "NoCasePointsError"]
