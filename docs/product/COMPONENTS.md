# COMPONENTS — Core UI Components

The recurring building blocks of the workspace. Full hierarchy and
composition rules live in
[../design/07_COMPONENT_HIERARCHY.md](../design/07_COMPONENT_HIERARCHY.md).

| Component | Role | Exists today |
|---|---|---|
| **Toolbar** | Contextual command strips (workspace top; per-panel headers). Dispatch commands only. | ✅ `components/Toolbar.tsx` |
| **Explorer** | IDE-style project tree (Source/Pages/Resources/Output/Reports), summarized counts | ✅ `panels/ExplorerPanel.tsx`, `ProjectTree.tsx` |
| **Viewer** | Page canvas: iframes, windowing, zoom, view modes | ✅ `viewer/` + `PreviewPane` |
| **Inspector / Properties** | Selected-object detail: Geometry / Typography / Appearance / Metadata / Advanced | ✅ basic; 2C grouped |
| **Status Bar** | Bottom strip: page x/y, zoom, selection, job state, env health | 🔜 (env badges exist in toolbar; consolidate) |
| **Log Panel** | Tailing log streams with level filtering | ✅ `LogPanel`; 2C adds stream tabs |
| **Progress** | Inline progress for pipeline stages and long tasks (never modal) | ✅ job polling; 2C Conversion Monitor |
| **Navigation** | NavRail (global + contextual groups); page nav controls; thumbnails | ✅ NavRail; thumbnails in 2B |
| **Search** | Incremental document search with jump-to-match highlight | 🔜 2B, `document/DocumentIndex.ts` |
| **Command Palette** | Ctrl+K fuzzy command runner over the Command Registry | 🔜 (registry seam exists) |
| **Tab Strip (CenterDock)** | Switches center panels; drives `?panel=`; activate/deactivate lifecycle | ✅ `panels/CenterDock.tsx` |
| **Empty / Placeholder states** | Honest "planned for 2C"-style placeholders, never fake UI | ✅ pattern established |
