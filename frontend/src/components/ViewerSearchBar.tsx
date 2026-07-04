import { useEffect, useRef, useState } from "react";

import { useDocumentManager } from "../context/DocumentManagerContext";
import { SearchMatch } from "../document/DocumentManager";
import { ViewerEngine } from "../viewer/ViewerEngine";
import { WorkspaceService } from "../workspace/WorkspaceService";

const DEBOUNCE_MS = 250;

interface ViewerSearchBarProps {
  engine: ViewerEngine;
  workspace: WorkspaceService;
  projectId: string;
  onClose: () => void;
}

/** Incremental document search (Ctrl+F): queries run through the Document
 * Manager's background-chunked index — results enrich progressively while
 * a large document is still being scanned — and every jump goes through
 * the one navigation + selection pipeline (navigateTo + highlightObject). */
export default function ViewerSearchBar({ engine, workspace, projectId, onClose }: ViewerSearchBarProps) {
  const documents = useDocumentManager();
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<SearchMatch[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [searching, setSearching] = useState(false);
  const [failed, setFailed] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const runRef = useRef(0);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const run = ++runRef.current;
    const stale = () => runRef.current !== run;
    setFailed(false);

    if (!query.trim()) {
      setMatches([]);
      setActiveIndex(-1);
      setSearching(false);
      return;
    }

    setSearching(true);
    const timer = setTimeout(() => {
      documents
        .search(projectId, query, (progress) => {
          if (!stale()) setMatches([...progress]);
        })
        .then((result) => {
          if (stale()) return;
          setMatches(result);
          // -1 = "no match visited yet": the counter reads 0/N and the
          // first Enter jumps to match 1.
          setActiveIndex(-1);
          setSearching(false);
        })
        .catch(() => {
          if (stale()) return;
          setSearching(false);
          setFailed(true);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [documents, projectId, query]);

  const jumpTo = (index: number) => {
    if (matches.length === 0) return;
    const wrapped = ((index % matches.length) + matches.length) % matches.length;
    setActiveIndex(wrapped);
    const match = matches[wrapped];
    workspace.navigateTo(match.page);
    engine.highlightObject(match.page, match.objectId);
  };

  const close = () => {
    engine.clearHighlight();
    onClose();
  };

  return (
    <div className="d-flex align-items-center gap-2 px-2 py-1 border-bottom lf-surface" role="search">
      <input
        ref={inputRef}
        className="form-control form-control-sm"
        style={{ maxWidth: 260 }}
        placeholder="Search document…"
        aria-label="Search document"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") jumpTo(event.shiftKey ? activeIndex - 1 : activeIndex + 1);
          if (event.key === "Escape") close();
        }}
      />
      <span className="small text-muted" style={{ minWidth: 64 }}>
        {failed
          ? "Search unavailable"
          : query.trim()
            ? `${activeIndex + 1 > 0 ? activeIndex + 1 : 0} / ${matches.length}${searching ? "…" : ""}`
            : ""}
      </span>
      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        title="Previous match (Shift+Enter)"
        disabled={matches.length === 0}
        onClick={() => jumpTo(activeIndex - 1)}
      >
        ▲
      </button>
      <button
        type="button"
        className="btn btn-sm btn-outline-secondary"
        title="Next match (Enter)"
        disabled={matches.length === 0}
        onClick={() => jumpTo(activeIndex + 1)}
      >
        ▼
      </button>
      <button type="button" className="btn btn-sm btn-outline-secondary ms-auto" title="Close (Esc)" onClick={close}>
        ✕
      </button>
    </div>
  );
}
