import { COMPACT_TILE, type TileSize } from './types';

export const GRID_COLUMNS = 4;

export type CellSize = { w: number; h: number };

export const TILE_CELLS: Record<TileSize, CellSize> = {
  '2x2': { w: 2, h: 2 },
  '4x1': { w: 4, h: 1 },
  '4x2': { w: 4, h: 2 },
  '4x4': { w: 4, h: 4 },
  '1x2': { w: 1, h: 2 },
  '1x4': { w: 1, h: 4 },
  '2x4': { w: 2, h: 4 },
  '3x4': { w: 3, h: 4 },
};

export type PackedTile<T> = {
  item: T;
  col: number;
  row: number;
  w: number;
  h: number;
};

/**
 * Packing v0: row-major, rank order. If a tile does not fit the remaining
 * width, start a new row and leave the gap. Never reorder to close a hole.
 */
export function packRowMajor<T>(
  items: T[],
  sizeOf: (item: T) => CellSize,
  columns = GRID_COLUMNS,
): { placements: PackedTile<T>[]; rowCount: number } {
  const placements: PackedTile<T>[] = [];
  let row = 0;
  let col = 0;
  let rowHeight = 0;

  for (const item of items) {
    const { w, h } = sizeOf(item);
    const width = Math.min(Math.max(w, 1), columns);
    const height = Math.max(h, 1);
    if (col + width > columns) {
      row += rowHeight > 0 ? rowHeight : 1;
      col = 0;
      rowHeight = 0;
    }
    placements.push({ item, col, row, w: width, h: height });
    col += width;
    rowHeight = Math.max(rowHeight, height);
  }

  const rowCount = placements.reduce((max, tile) => Math.max(max, tile.row + tile.h), 0);
  return { placements, rowCount };
}

export function cellsForTile(size: TileSize | null | undefined): CellSize {
  return TILE_CELLS[size ?? COMPACT_TILE] ?? TILE_CELLS[COMPACT_TILE];
}
