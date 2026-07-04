import { ReactNode, useEffect, useState } from "react";

import { Badge, Skeleton } from "./ui";
import { useDocumentManager } from "../context/DocumentManagerContext";
import { IdmFont, IdmObject } from "../document/idmTypes";
import { SelectionInfo } from "../viewer/types";

interface PropertiesPanelProps {
  selection: SelectionInfo | null;
  projectId: string | null;
}

function Group({ title, defaultOpen = true, children }: { title: string; defaultOpen?: boolean; children: ReactNode }) {
  return (
    <details open={defaultOpen} className="lf-propgroup border-bottom">
      <summary className="small fw-semibold px-3 py-1" style={{ cursor: "pointer" }}>
        {title}
      </summary>
      <dl className="small px-3 pb-2 mb-0">{children}</dl>
    </details>
  );
}

function Row({ label, value }: { label: string; value: ReactNode }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="d-flex gap-2 py-1">
      <dt className="text-muted" style={{ width: 92, flex: "none", fontWeight: 400 }}>
        {label}
      </dt>
      <dd className="mb-0 text-break" style={{ fontFamily: "var(--lf-font-mono)", fontSize: "var(--lf-fs-xs)" }}>
        {value}
      </dd>
    </div>
  );
}

const num = (value: number) => Math.round(value * 100) / 100;

/** Grouped object inspector (2C): Geometry / Typography / Appearance /
 * Metadata / Advanced, resolved through the Document Manager (never a raw
 * idm.json fetch). Shows only real IDM data — confidence is intentionally
 * never fabricated (standing decision). */
export default function PropertiesPanel({ selection, projectId }: PropertiesPanelProps) {
  const documents = useDocumentManager();
  const [object, setObject] = useState<IdmObject | null>(null);
  const [font, setFont] = useState<IdmFont | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let stale = false;
    setObject(null);
    setFont(null);
    if (!selection || !projectId) return;
    setLoading(true);
    documents
      .getObject(projectId, selection.objectId)
      .then(async (resolved) => {
        if (stale) return;
        setObject(resolved ?? null);
        if (resolved?.type === "text" && resolved.element.font_id) {
          const resolvedFont = await documents.getFont(projectId, resolved.element.font_id);
          if (!stale) setFont(resolvedFont ?? null);
        }
      })
      .finally(() => {
        if (!stale) setLoading(false);
      });
    return () => {
      stale = true;
    };
  }, [documents, projectId, selection]);

  return (
    <aside className="lf-panel lf-surface d-flex flex-column h-100">
      <div className="d-flex align-items-center gap-2 px-3 py-2 border-bottom">
        <h6 className="text-uppercase text-muted small mb-0">Properties</h6>
        {object && <Badge status="neutral">{object.type}</Badge>}
      </div>

      {!selection ? (
        <p className="text-muted small p-3">Click any object on the page.</p>
      ) : loading ? (
        <div className="p-3 d-flex flex-column gap-2">
          <Skeleton height={12} />
          <Skeleton height={12} width="70%" />
          <Skeleton height={12} width="85%" />
        </div>
      ) : !object ? (
        <div className="p-3">
          <p className="text-muted small mb-1">Object not found in the document model.</p>
          <p className="text-muted small mb-0" style={{ fontFamily: "var(--lf-font-mono)" }}>{selection.objectId}</p>
        </div>
      ) : (
        <div className="flex-grow-1 overflow-auto">
          <Group title="Geometry">
            <Row label="x" value={num(object.element.bbox.x)} />
            <Row label="y" value={num(object.element.bbox.y)} />
            <Row label="width" value={num(object.element.bbox.width)} />
            <Row label="height" value={num(object.element.bbox.height)} />
            {"rotation" in object.element && <Row label="rotation" value={`${object.element.rotation}°`} />}
            {"z_index" in object.element && <Row label="z-index" value={object.element.z_index} />}
          </Group>

          {object.type === "text" && (
            <Group title="Typography">
              <Row label="font" value={font ? font.family : object.element.font_id ?? "—"} />
              {font && !font.filename && (
                <Row label="web font" value={<Badge status="warning">fallback — not embedded</Badge>} />
              )}
              <Row label="size" value={`${num(object.element.font_size)} pt`} />
              <Row label="line height" value={`${num(object.element.line_height)} pt`} />
              <Row label="color" value={object.element.color} />
              <Row label="alignment" value={object.element.alignment} />
              <Row label="direction" value={object.element.writing_direction} />
            </Group>
          )}

          <Group title="Appearance">
            {object.type === "text" && <Row label="color" value={object.element.color} />}
            {object.type === "shape" && (
              <>
                <Row label="kind" value={object.element.kind} />
                <Row label="fill" value={object.element.fill_color ?? "none"} />
                <Row label="stroke" value={object.element.stroke_color ?? "none"} />
                <Row label="stroke width" value={num(object.element.stroke_width)} />
              </>
            )}
            {object.type === "image" && <Row label="asset" value={object.element.asset_id} />}
          </Group>

          <Group title="Metadata">
            <Row label="object id" value={object.element.id} />
            <Row label="page" value={object.page} />
            <Row label="type" value={object.type} />
          </Group>

          {object.type === "text" && (
            <Group title="Advanced" defaultOpen={false}>
              <Row label="origin x" value={num(object.element.origin_x)} />
              <Row label="origin y" value={num(object.element.origin_y)} />
              <Row label="ascender" value={num(object.element.ascender)} />
              <Row label="descender" value={num(object.element.descender)} />
              <Row label="reading order" value={object.element.reading_order} />
              <Row label="spans" value={object.element.spans.length} />
              {font && (
                <>
                  <Row label="font file" value={font.filename ?? "none"} />
                  <Row label="subset" value={font.subset ? "yes" : "no"} />
                </>
              )}
            </Group>
          )}
        </div>
      )}
    </aside>
  );
}
