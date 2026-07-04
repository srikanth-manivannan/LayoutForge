# SCREEN_LIST — Every Screen in LayoutForge Studio

**Rule inherited from 2A (do not regress):** the Workspace is ONE screen
hosting many dockable panels/tabs — Compare, Validation, Properties, Logs
are *panels inside the Workspace*, never separate page destinations. This
matches how desktop publishing software behaves.

## Global screens (NavRail destinations, top group)

| Screen | Route | Purpose |
|---|---|---|
| Dashboard | `/` | Production overview, recent projects, active conversion |
| Projects (Project Explorer) | `/projects` | All projects: list, search, open, delete |
| Import (Conversion) | `/conversion` | Upload + pipeline monitoring |
| Settings | `/settings` | Preferences, theme, keybindings |
| About | (Settings sub-view or modal) | Version, licenses, credits |

## The Workspace (one screen, many panels)

| Screen | Route | Purpose |
|---|---|---|
| Workspace | `/workspace/:projectId` | The production environment for one title |

Docked/tabbed panels inside the Workspace (`?panel=` is the source of truth
for the active center tab):

- **Explorer** (left dock) — IDE-style project tree
- **Viewer** (center tab) — page rendering, thumbnails, search
- **Compare** (center tab) — overlay / split proofing
- **Validation** (center tab) — automated check results
- **Accessibility** (center tab, Phase 5) — reading order + a11y remediation
- **Export** (center tab or modal flow, Phase 4) — format, options, package
- **Properties** (right dock) — selected-object inspector
- **Logs** (bottom dock) — application / conversion / performance streams
- **Conversion Monitor** (bottom dock tab, 2C) — live stage/ETA/queue

## Future screens (reserved, do not design into a corner)

- Batch Queue (Phase 7) — many titles, statuses, priorities
- Review / Annotations (Future) — comments, approvals, collaboration
- Plugin Marketplace (Future)
- Admin / Team Management (Phase 7 Enterprise)
