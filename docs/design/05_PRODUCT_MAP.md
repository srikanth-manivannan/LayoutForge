# 05 — Product Map

The whole product on one page: modules × phases × surfaces.

```
                        LAYOUTFORGE STUDIO
                              │
   ┌──────────────┬───────────┼────────────────┬─────────────┐
   ▼              ▼           ▼                ▼             ▼
 INTAKE        PRODUCTION   QUALITY         DELIVERY      PLATFORM
   │              │           │                │             │
 Dashboard     Workspace    Validation       Export        Settings
 Import        Viewer       Compare          (HTML ✅,     Command system ✅
 (Batch P7)    Explorer     Accessibility     EPUB P4,     Event bus ✅
 (Watch        Properties    (P5)             ZIP,         Document Manager ✅
  folders P7)  Editing (P3) AI assist (P6)    Reports)     Plugins (reserved)
               Assets       Review (future)  (Delivery     Enterprise (P7)
               Logs/Monitor                   tracking P7)  Marketplace (future)
```

## Module × Phase matrix

| Module | P1 Engine | P2 Workspace | P3 Editing | P4 Publishing | P5 A11y | P6 AI | P7 Enterprise |
|---|---|---|---|---|---|---|---|
| Dashboard | — | ✅ overview | | | | | queues, teams |
| Import | ✅ upload+pipeline | monitor (2C) | | | | | batch, watch, API |
| Workspace shell | — | ✅ 2A | edit toolbar | | | | |
| Viewer | ✅ core | 2B: windowing, modes, search | edit handles | spread/EPUB preview | reading-order overlay | | |
| Compare | debug view ✅ | 2C panel | before/after edits | | | | |
| Validation | — | 2C engine (worker) | live re-check | export preflight | a11y checks | AI suggestions | policy packs |
| Accessibility | — | — | — | — | ✅ full module | AI alt text | conformance reports |
| Assets | ✅ extraction+dedup | Explorer groups | replace font/image | | | | |
| Export | HTML/CSS ✅ | manifest/ZIP | | EPUB r+FXL | a11y metadata | | bulk, delivery |
| Settings | — | basics | keybindings | export presets | | AI config | admin, SSO, audit |

## Surface inventory (where users touch each module)

- **Screens (routes):** Dashboard · Projects · Import · Settings · Workspace
- **Center tabs:** Viewer · Compare · Validation · [A11y] · [Export]
- **Docks:** Explorer · Properties · Logs/Conversion Monitor
- **Overlays:** Command palette · context menus · toasts · go-to-page
- **Non-UI surfaces:** REST API · static project mount · (P7) webhooks/CLI

## Boundaries (what LayoutForge is NOT)

- Not a PDF *authoring* tool — the source of truth arrives as a finished PDF.
- Not a generic file converter — publishing formats only, fidelity first.
- Not a DAM/CMS — Assets exist per-project; a library is future-marketplace
  territory at most.
- Not OCR-first — born-digital PDFs are the target corpus (OCR is an
  explicit non-goal from docs/00_VISION.md).
