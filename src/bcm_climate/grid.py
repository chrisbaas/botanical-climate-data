"""Stable 0.25-degree cell IDs. Geographic grids are not kilometre squares."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Cell:
    row: int
    col: int
    lat: float
    lon: float

    @property
    def id(self) -> str:
        return f"g025_r{self.row:04d}_c{self.col:04d}"

def cells_for_bbox(west: float, south: float, east: float, north: float):
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Bbox must be ordered and within -180..180 / -90..90; split antimeridian tiles")
    if any(abs(v * 4 - round(v * 4)) > 1e-7 for v in (west,south,east,north)):
        raise ValueError("Bbox edges must align to a 0.25-degree grid")
    for row in range(int(round((south + 90)*4)), int(round((north + 90)*4))):
        for col in range(int(round((west + 180)*4)), int(round((east + 180)*4))):
            yield Cell(row, col, round(-90 + (row + 0.5)*.25, 6), round(-180 + (col+.5)*.25, 6))
