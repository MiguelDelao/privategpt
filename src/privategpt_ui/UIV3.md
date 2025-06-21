# Sandbox UI – V3 Design Specification (Monochrome + Subtle Accent)

> Version 3 focuses on a near-black / off-white monochrome palette with a *minimal* accent (muted blue) used only for primary actions and focus rings.  The goal is a slick, high-tech feel that avoids bright colours while preserving clear affordances through motion and hierarchy.

---

## 0. Visual Language
1. 🕶 **Monochrome Foundation** – dark grays for chrome surfaces, soft off-white workspace.
2. ✨ **Quiet Accent** – desaturated blue (`#4F5DFF`) appears sparingly (links, focused buttons).
3. 🪶 **Micro-motion** – 120-200 ms ease-out transitions; 3 D transforms on press.
4. 🩺 **Accessibility** – WCAG AA contrast (≥ 4.5:1) between text & background.

---

## 1. Colour Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-outer` | #0E0F11 | Body background, sidebar, chat panel |
| `--bg-elevated` | #181A1D | Raised surfaces (sidebar hover, chat header) |
| `--bg-workspace` | #F5F5F7 | Main editor / dashboard background |
| `--border-subtle` | #2A2D32 | Dividers, outlines |
| `--text-primary-dark` | #EDEDED | Text on dark background |
| `--text-secondary-dark` | #9CA0A6 | Muted text on dark |
| `--text-primary-light` | #141414 | Text on light background |
| `--accent` | #4F5DFF | Primary action, focus ring |
| `--destructive` | #EF4444 | Delete / danger |

All tokens available both as CSS variables (`var(--bg-outer)`) and Tailwind utilities via `theme.extend.colors`.

---

## 2. Layout Recap
Unchanged from V2: three-pane grid `[264px 1fr 320px]` on ≥ 768px screens, collapsing panels on mobile.

---

## 3. Component Updates
### 3.1 Sidebar
• Background: `--bg-outer`  
• Hover: `--bg-elevated`  
• Active nav: 3 px left border in `--accent`  
• Button text: `--text-secondary-dark` → `--text-primary-dark` on hover.  
• New Chat button becomes *ghost* style with border `--border-subtle`; border & text turn `--accent` on hover.

### 3.2 Workspace
• Background: `--bg-workspace`  
• Tab bar: dark-gray strip (`--bg-elevated`), active tab underline `--accent`.

### 3.3 Chat Panel
• Same dark chrome (`--bg-outer`); header uses `--bg-elevated`.  
• User bubble: gradient from `--accent` → 90 % opacity.  
• Assistant bubble: `--bg-elevated`.

### 3.4 Motion Guidelines (refined)
| Interaction | Animation |
|-------------|-----------|
| Button hover | `translateY(-1px)` + shadow `md` (120 ms) |
| Button active | `translateY(0)` + shadow `sm` (80 ms) |
| Tab switch | `opacity` fade (100 ms) + slide (4 px) |
| Sidebar collapse | width spring `stiff` (200 ms) |

---

## 4. Typography
| Style | Size | Weight | Tracking |
|-------|------|--------|----------|
| h1 | 28px | 700 | -0.02em |
| h2 | 20px | 600 | -0.01em |
| body | 14px | 400 | normal |
| mono | 13px | 500 | 0.02em |

Font family remains **Geist** (sans & mono).

---

## 5. Tailwind Mapping
Add to `tailwind.config.ts`:
```ts
extend: {
  colors: {
    outer: "#0E0F11",
    elevated: "#181A1D",
    workspace: "#F5F5F7",
    "border-subtle": "#2A2D32",
    "text-dark": "#EDEDED",
    "text-muted-dark": "#9CA0A6",
    "text-light": "#141414",
    accent: "#4F5DFF",
    destructive: "#EF4444",
  },
}
```

---

## 6. Implementation Checklist
1. Update Tailwind config with new tokens. ✅  
2. Replace existing `brand` utility with `accent`.  
3. Adjust component classes:  
   • `bg-bg-elevated` → `bg-outer` / `bg-elevated`  
   • `hover:text-brand` → `hover:text-accent`  
   • Active nav border `border-l-2 border-accent`.  
4. Ensure dark mode is default (`<html class="dark">`).  
5. Remove any leftover bright blue (#3B82F6).

> **v3 drafted – ready for build** 