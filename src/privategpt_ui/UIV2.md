# Sandbox UI – V2 Design Specification (Modern ChatGPT-Style)

> Goal: Replace the original *UI.md* with a sleeker, more cohesive interface that feels indistinguishable from the latest OpenAI Chat UI while retaining the three-pane legal workspace concept.

---

## 0. Design Principles
1. ✨ **Calm Aesthetic** – low-contrast dark surfaces with soft highlights.
2. 📐 **Spatial Clarity** – clean grids, generous padding, zero visual clutter.
3. ⚡ **Subtle Motion** – 150–200 ms ease-out transitions; no jarring slides.
4. 🧩 **Component Re-use** – one design language across Sidebar, Workspace, Chat.
5. 🛡️ **Legal Trust** – professional fonts (Inter / Geist Sans), clear approvals.

---

## 1. Color System (Semantic Tokens)
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `--bg-default` | #111317 | #ffffff | Primary page background |
| `--bg-elevated` | #1A1D21 | #f9fafb | Card/panel background |
| `--border-subtle` | #2A2D32 | #e5e7eb | Dividers, outlines |
| `--text-primary` | #ECEDEE | #111827 | Body text |
| `--text-secondary` | #A1A6AD | #4b5563 | Sub-text, placeholders |
| `--brand` | #3B82F6 | #2563eb | Links, accents |
| `--brand-emphasis` | #60A5FA | #1d4ed8 | Button hovers |
| `--success` | #10B981 | #059669 | Approved badge |
| `--warning` | #F59E0B | #d97706 | Pending review |
| `--danger` | #EF4444 | #b91c1c | Destructive actions |

All colors exposed as CSS variables to allow easy theming.

---

## 2. Layout Grid (Desktop ≥ 1200 px)
```
┌─────────────264px────────────┬─────────────flex─────────────┬──320px──┐
│         SIDEBAR              │           WORKSPACE           │  CHAT   │
│ Dark, scroll-y               │ Light, tabbed                │ Dark    │
└──────────────────────────────┴──────────────────────────────┴──────────┘
```

• `height: 100dvh` to respect mobile address-bar shrink.
• `overflow: hidden` on root; internal panes manage scroll.
• Use `framer-motion` *layout* prop for smooth pane toggles.

---

## 3. Sidebar (Left)
### 3.1 Structure
```
[ New Chat ▾ ]  (Button)
────────────────────────
Dashboard
Documents
Settings          ⚙
────────────────────────
<Dynamic Area>
```
*Width collapsible* to 72 px (icon-only) via `cmd+b`.

### 3.2 Components
1. **New Chat Button**  
   • Style: *brand-ghost* (bordered), rounded-md.  
   • Left icon `MessageSquarePlus`.  
   • Hover: bg `--brand`⁄10, border `--brand`⁄40.  
   • Click → opens blank chat tab & focuses composer.
2. **Nav Items**  
   • Stack of *ghost buttons* (transparent).  
   • Active state: bg `--brand`⁄15, text `--text-primary`.
3. **Separator**  
   • `border-t` using `--border-subtle`, margin-y-2.
4. **Dynamic Content**  
   • *Mode = Chat*: scrollable chat history list.  
   • *Mode = Docs*: tree view (see 5.1).
5. **Notification Badge**  
   • When a new AI response arrives in background chat, show blue dot on corresponding list item.

### 3.3 Animation
| Interaction | Spec |
|-------------|------|
| Hover nav button | `background-color` fade 150 ms ease-out |
| Collapse/expand | width spring (`framer-motion`, 240 ms) |

---

## 4. Workspace (Center)
### 4.1 Tab Bar
| Property | Value |
|----------|-------|
| Height | 46 px |
| Background | `--bg-elevated` |
| Border-bottom | 1 px solid `--border-subtle` |

**Tab**  
• Padding: 0 14 px.  
• Active: bg `--bg-default`, bottom-border `--brand` 2 px.  
• Close-icon appears on hover (fade-in 100 ms).

### 4.2 Content Region
• `overflow: auto;` *smooth-scroll*.  
• Use **TipTap** with `@tiptap/extension-collaboration-cursor` for future multi-user.

---

## 5. Document Mode Enhancements
### 5.1 File Tree
Use `@headlessui/react` + `react-dnd-kit` for drag-reorder.  
Folder chevron rotates via transform (200 ms ease).

### 5.2 Editor Toolbar
Buttons: ghost style, icon-only by default; tooltip on hover.  
Group buttons in rounded containers (similar to Figma).

---

## 6. Chat Panel (Right)
### 6.1 Header
| Element | Style |
|---------|-------|
| Height | 54 px |
| Background | `--bg-elevated` |
| Title | font-medium 14 px, `--text-primary` |
| Collapse btn | `ChevronRight`, rotates 180° when expanded |

### 6.2 Message List
• Virtually scrolled (`react-virtuoso`) for long chats.  
• Streaming token animation: caret blink + `opacity` keyframes.  
• Assistant bubble shows *approval toolbar* (Approve / Regenerate) floating on hover.

### 6.3 Composer
| Feature | Spec |
|---------|------|
| Auto-grow | up to 6 lines then scroll |
| `/` Commands | slash menu (insert docs, clauses) |
| Send hotkey | `Cmd+Enter` |

### 6.4 Theme
Assistant bubble: bg `--bg-elevated`; User: `--brand` shade.  
Rounded-xl 18 px radius; max-width 78 %.

---

## 7. Notification System
• **Toast Stack** (bottom-right) using `@radix-ui/react-toast`.  
• Types: `success`, `error`, `info`.  
• Auto dismiss 4 s, pause on hover.

---

## 8. Motion & Micro-interaction Guidelines
| Element | Animation |
|---------|-----------|
| Buttons | translate-y ‑1 px on active (20 ms), shadow drop |
| Tab switch | fade-through 120 ms via `framer-motion` `AnimatePresence` |
| File drag | elevate 8 px shadow, scale 1.03 |
| Chat incoming | slide-up + fade (staggered children 40 ms) |

---

## 9. Accessibility
• Focus ring: 2 px `--brand` `outline-offset: 2px`.  
• Prefers-reduced-motion: disable non-essential animations.  
• ARIA roles on tree, tabs, chat log.

---

## 10. Responsive Behaviour
| Breakpoint | Behaviour |
|------------|-----------|
| ≥768 px | Three-pane layout as described |
| 640-767 px | Sidebar overlays (off-canvas, swipe-in), Chat panel collapses |
| <640 px | Only Workspace visible; floating action button toggles chat |

---

## 11. Component Library Mapping (shadcn/ui)
| UI Element | shadcn Primitive |
|------------|-----------------|
| Sidebar Buttons | `Button` variant="ghost" size="sm" |
| Separators | `Separator` orientation="horizontal" |
| Tabs | `Tabs` root & list |
| Toasts | `Toast` |
| Dialogs | `Dialog` (for settings, share) |

---

## 12. Next Steps
1. Implement this tokenized color system in `tailwind.config.ts` (`extend.colors`).
2. Refactor `Sidebar` to new structure + collapse.
3. Apply new chat bubble components & streaming animations.

> **Version 2 drafted – ready for critique & iteration.** 