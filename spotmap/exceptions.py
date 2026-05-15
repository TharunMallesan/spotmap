class SpotMapError(Exception):
    pass


class ColumnNotFoundError(SpotMapError):
    pass


class NoCasePointsError(SpotMapError):
    pass
