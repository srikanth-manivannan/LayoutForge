# 07 — Component Hierarchy

Maps design components to the shipped frontend structure. Names in `code`
already exist; ◆ marks components to build.

```
AppProviders (contexts: EventBus · Command · DocumentManager · ViewerEngine · Workspace)
└── ShellLayout
    ├── NavRail                      global + contextual groups
    ├── ◆ StatusBar                  consolidates env badges · job state · page/zoom/selection
    ├── ◆ CommandPalette             overlay; renders CommandRegistry entries
    ├── ◆ ToastLayer                 job-ready, export-done notifications
    └── <Outlet/>
        ├── DashboardPage
        │   ├── ◆ ImportDropZone     (shared with Import screen)
        │   ├── ◆ ActiveConversionCard → reuses ConversionMonitor internals
        │   └── ◆ ProjectCardGrid
        ├── ProjectsPage             ◆ virtualized ProjectTable + toolbar
        ├── ConversionPage           ◆ ImportDropZone + ◆ PipelineStageList
        ├── SettingsPage             ◆ SettingsCategoryList + forms
        └── WorkspacePage
            ├── ◆ QuickActionsBar    Import · Compare · Validate · A11y · Export ·
            │                        Search · Command Palette — commands only,
            │                        identical in every mode; nothing else here
            └── ProductionWorkspaceLayout        (resizable panel groups, persisted)
                ├── ExplorerPanel · ProjectTree   (left dock; via DocumentManager only)
                ├── CenterDock                    (Workspace MODES; drives ?panel=; activate/deactivate)
                │   ├── ViewerPanel
                │   │   ├── ◆ ViewerToolbar      page nav · zoom · fit · view mode · search
                │   │   ├── ◆ ThumbnailRail      2B; windowed plain <img>
                │   │   ├── PreviewPane → ViewerPageHost   (thin React shells)
                │   │   │   └── [viewer/ engine: Viewport · IframeRenderer · Selection
                │   │   │        NavigationManager · ZoomManager — NOT React]
                │   │   └── ◆ SearchBar          2B; DocumentIndex via DocumentManager
                │   ├── ◆ ComparePanel           2C; mode switch + OpacitySlider + SplitView
                │   ├── ◆ ValidationPanel        2C; FindingsTable + RunControls (Web Worker)
                │   ├── ◆ A11yPanel              P5; ReadingOrderList + AltTextEditor
                │   └── ◆ ExportPanel            P4; FormatCards + OptionsForm + PackageList
                ├── PropertiesPanel              (right dock)
                │   └── ◆ PropertyGroup ×5       Geometry/Typography/Appearance/Metadata/Advanced
                ├── ◆ AIAssistantPanel           P6; right-dock tab beside Properties —
                │                                a panel, NEVER a chatbot/screen; runs
                │                                ai.* commands (Fix Alignment · Find
                │                                Missing Fonts · Generate Alt Text ·
                │                                Validate Reading Order) with reviewable,
                │                                undoable results
                └── ◆ BottomDock (tabbed)
                    ├── LogPanel                 (exists; gains stream tabs 2C)
                    └── ◆ ConversionMonitor      2C; live stage/ETA/queue
```

## Composition rules (how components are allowed to talk)

1. **Controls → commands.** Toolbars, menus, palette, shortcuts all dispatch
   through `CommandRegistry`. No component calls WorkspaceService/engine
   directly. (Shipped rule.)
2. **Data → DocumentManager.** Panels request the slice they need (summary,
   page, object); nobody fetches `idm.json` or calls the summary API
   directly. (Shipped rule.)
3. **Cross-panel reactions → EventBus.** SelectionChanged populates
   Properties; ValidationFinding-click emits navigate+select; JobFinished
   raises a toast. Panels never import each other.
4. **Dockable panels implement `WorkspacePanelDescriptor`** (`id, title,
   icon, activate/deactivate/dispose, commands()`), so future panels — and
   eventually third-party plugin panels — mount uniformly.
5. **Primitive layer** (◆ to standardize as `components/ui/`): Button,
   IconButton, Tabs, Tree, VirtualTable, Badge, Toolbar, Slider, Progress,
   EmptyState, Skeleton — Bootstrap-compatible, tokens-only styling. Feature
   panels compose primitives; primitives never know about the domain.

## Reuse ledger (build once, use everywhere)

| Component | Used by |
|---|---|
| PipelineStageList | Import screen · ActiveConversionCard · ConversionMonitor |
| ImportDropZone | Dashboard · Import screen |
| FindingsTable | Validation · A11y (P5) · export preflight (P4) |
| Page canvas (viewer engine) | Viewer · Compare · A11y overlay · P3 editing |
| Badge (status taxonomy) | Dashboard · Projects · Explorer · Monitor |
