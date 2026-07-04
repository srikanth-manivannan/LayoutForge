import { useEffect, useState } from "react";

import { ProjectSummary } from "../api/client";
import { useDocumentManager } from "../context/DocumentManagerContext";

interface ProjectTreeProps {
  projectId: string;
}

const MAX_LISTED_ITEMS = 20; // never dump thousands of DOM nodes for a 2,000-page document

function TreeSection({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="lf-tree-section">
      <button type="button" className="lf-tree-section-toggle" onClick={() => setOpen((v) => !v)}>
        <span className="lf-tree-caret">{open ? "▾" : "▸"}</span> {title}
      </button>
      {open && <div className="lf-tree-section-body">{children}</div>}
    </div>
  );
}

/** The IDE-style breakdown of one project: Source / Pages / Resources /
 * Output / Reports. Deliberately summarizes counts rather than listing every
 * page/asset — a 2,000-page, 50,000-image document must never force this
 * tree to render tens of thousands of DOM nodes (Large Document Architecture
 * memory rules). */
export default function ProjectTree({ projectId }: ProjectTreeProps) {
  const documentManager = useDocumentManager();
  const [summary, setSummary] = useState<ProjectSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setSummary(null);
    setError(null);
    documentManager
      .getSummary(projectId)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load project summary.");
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, documentManager]);

  if (error) return <div className="text-danger small p-2">{error}</div>;
  if (!summary) return <div className="text-muted small p-2">Loading project…</div>;

  const { statistics, manifest, health, warnings } = summary;
  const fonts = manifest?.fonts ?? [];

  return (
    <div className="lf-tree">
      <TreeSection title="Source">
        <div className="lf-tree-leaf">{summary.project.filename}</div>
      </TreeSection>

      <TreeSection title={`Pages (${statistics.page_count})`}>
        {manifest ? (
          <>
            {manifest.pages.slice(0, MAX_LISTED_ITEMS).map((page) => (
              <div key={page.number} className="lf-tree-leaf">
                Page {page.number} — {Math.round(page.width)}×{Math.round(page.height)}
                {page.rotation ? ` (${page.rotation}°)` : ""}
              </div>
            ))}
            {statistics.page_count > MAX_LISTED_ITEMS && (
              <div className="lf-tree-leaf text-muted">+{statistics.page_count - MAX_LISTED_ITEMS} more</div>
            )}
          </>
        ) : (
          <div className="lf-tree-leaf text-muted">Not yet processed.</div>
        )}
      </TreeSection>

      <TreeSection title="Resources">
        <div className="lf-tree-subsection">
          <div className="lf-tree-subsection-title">Fonts ({statistics.font_count})</div>
          {fonts.slice(0, MAX_LISTED_ITEMS).map((font) => (
            <div key={font.id} className="lf-tree-leaf">
              {font.family} — {font.weight}/{font.style}
              {font.embedded ? "" : " (system)"}
            </div>
          ))}
          {statistics.font_count > MAX_LISTED_ITEMS && (
            <div className="lf-tree-leaf text-muted">+{statistics.font_count - MAX_LISTED_ITEMS} more</div>
          )}
        </div>
        <div className="lf-tree-subsection">
          <div className="lf-tree-subsection-title">Images ({statistics.image_count})</div>
        </div>
        <div className="lf-tree-subsection">
          <div className="lf-tree-subsection-title">CSS ({statistics.css_file_count} files)</div>
        </div>
      </TreeSection>

      <TreeSection title="Output">
        <div className="lf-tree-leaf">HTML ({statistics.html_file_count} files)</div>
        <div className="lf-tree-leaf">Manifest — {health.idm_ok ? "available" : "not yet generated"}</div>
      </TreeSection>

      <TreeSection title="Reports">
        <div className="lf-tree-leaf">
          Validation — {warnings.length > 0 ? `${warnings.length} warning(s)` : "no warnings"}
        </div>
        <div className="lf-tree-leaf text-muted">Full validation engine: sub-phase 2C.</div>
      </TreeSection>

      {warnings.length > 0 && (
        <div className="lf-tree-warnings">
          {warnings.map((warning) => (
            <div key={warning} className="small text-warning-emphasis">
              ⚠ {warning}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
