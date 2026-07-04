/** Mirrors the backend IDM's `to_dict()` shapes (see
 * backend/app/pipeline/document.py and backend/app/pipeline/elements/).
 * Only the fields the frontend actually consumes (Properties, search,
 * future validation) are declared. */

export interface IdmBoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface IdmTextSpan {
  text: string;
  font_id: string | null;
  font_size: number;
  color: string;
}

export interface IdmTextBlock {
  id: string;
  page: number;
  bbox: IdmBoundingBox;
  text: string;
  font_id: string | null;
  font_size: number;
  color: string;
  alignment: string;
  rotation: number;
  reading_order: number;
  line_height: number;
  letter_spacing: number;
  word_spacing: number;
  writing_direction: string;
  origin_x: number;
  origin_y: number;
  ascender: number;
  descender: number;
  spans: IdmTextSpan[];
}

export interface IdmImageElement {
  id: string;
  asset_id: string;
  bbox: IdmBoundingBox;
  rotation: number;
  z_index: number;
}

export interface IdmShapeElement {
  id: string;
  kind: string;
  bbox: IdmBoundingBox;
  fill_color: string | null;
  stroke_color: string | null;
  stroke_width: number;
  z_index: number;
}

export interface IdmPage {
  number: number;
  width: number;
  height: number;
  rotation: number;
  background_image: string | null;
  text_blocks: IdmTextBlock[];
  images: IdmImageElement[];
  shapes: IdmShapeElement[];
  fonts_used: string[];
}

export interface IdmFont {
  id: string;
  original_name: string;
  family: string;
  weight: string;
  style: string;
  embedded: boolean;
  subset: boolean;
  encoding: string | null;
  filename: string | null;
}

export interface IdmAsset {
  id: string;
  type: string;
  filename: string;
  path: string;
  hash: string;
  width: number | null;
  height: number | null;
  referenced_pages: number[];
}

export interface IdmDocument {
  project_id: string;
  metadata: {
    title: string | null;
    author: string | null;
    page_count: number;
  };
  pages: IdmPage[];
  fonts: IdmFont[];
  assets: IdmAsset[];
}

/** The union of element kinds Properties/Selection can resolve to. */
export type IdmObject =
  | { type: "text"; page: number; element: IdmTextBlock }
  | { type: "image"; page: number; element: IdmImageElement }
  | { type: "shape"; page: number; element: IdmShapeElement };
