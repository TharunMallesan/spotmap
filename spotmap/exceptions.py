"""
spotmap/exceptions.py
=====================
Custom exceptions for the SpotMap package.
All errors raised by SpotMap will be one of these types,
so users can catch them specifically.
"""


class SpotMapError(Exception):
    """Base exception for all SpotMap errors."""
    pass


class ColumnDetectionError(SpotMapError):
    """Raised when lat/lon/outcome columns cannot be detected automatically."""
    pass


class BoundaryFileError(SpotMapError):
    """Raised when boundary files cannot be found, downloaded, or read."""
    pass


class NoDataError(SpotMapError):
    """Raised when the CSV has no valid case points after filtering."""
    pass


class CSVError(SpotMapError):
    """Raised when the CSV file cannot be read or is empty."""
    pass