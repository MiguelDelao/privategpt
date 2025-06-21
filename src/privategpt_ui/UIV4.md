# Sandbox UI – V4 Design Specification (Polished & Modern)

> **Self-Critique of V3**: Too harsh, grid-like, amateurish. V4 focuses on **soft elegance** with warmer grays, rounded corners, subtle depth, and living demo content.

---

## 🎨 Color Palette (Warmer & Softer)
| Token | Hex | Usage |
|-------|-----|-------|
| `surface-primary` | #1C1C1E | Main sidebar/panel background (warmer than pure black) |
| `surface-secondary` | #2C2C2E | Elevated elements, hover states |
| `surface-tertiary` | #3A3A3C | Active states, selection |
| `workspace-bg` | #FAFAFA | Main content area (softer than pure white) |
| `border-soft` | #48484A | Subtle borders and dividers |
| `text-primary` | #F2F2F7 | Primary text on dark |
| `text-secondary` | #8E8E93 | Secondary text, muted |
| `text-dark` | #1D1D1F | Text on light backgrounds |
| `accent-blue` | #007AFF | Primary actions, focus states |
| `accent-hover` | #0051D5 | Hover states for accent |

---

## 🏗 Layout Principles
1. **Soft Containers** - rounded corners (8px), subtle shadows
2. **Breathing Room** - generous padding (16-24px)
3. **Organic Flow** - avoid hard grid lines, use subtle borders
4. **Visual Hierarchy** - typography scale, proper weights
5. **Living Content** - real demo data, not placeholders

---

## 📐 Component Specifications

### Sidebar (Left Panel)
```css
background: surface-primary
border-radius: 0 12px 12px 0
padding: 20px 16px
box-shadow: 0 1px 3px rgba(0,0,0,0.12)
```

**New Chat Button:**
- Full rounded (12px)
- Subtle border: `border-soft`
- Hover: lift effect + accent border
- Icon + text, proper spacing

**Navigation Items:**
- Rounded corners (8px)
- Hover: `surface-secondary` background
- Active: `surface-tertiary` + left accent border (3px)
- Icons: 18px, proper alignment

**Chat History List:**
- Real demo chats: "Contract Review", "NDA Draft", "Client Email"
- Hover: subtle background
- Time stamps: "2m ago", "1h ago"
- Overflow with fade

### Workspace (Center)
```css
background: workspace-bg
border-radius: 12px
margin: 12px
box-shadow: 0 1px 3px rgba(0,0,0,0.05)
```

**Typography:**
- H1: 32px, weight 600, letter-spacing tight
- Body: 16px, line-height 1.6
- Color: `text-dark`

### Chat Panel (Right)
```css
background: surface-primary
border-radius: 12px 0 0 12px
border-left: 1px solid border-soft
```

**Demo Messages:**
- User: "Review this contract for compliance issues"
- Assistant: Multi-line response with proper formatting
- Streaming dots animation for live feel
- Message bubbles: rounded, proper spacing

**Input Area:**
- Auto-growing textarea
- Subtle border, focus ring
- Send button: accent-blue, rounded

---

## ✨ Micro-Interactions
| Element | Animation |
|---------|-----------|
| Button hover | translateY(-1px) + shadow lift (150ms) |
| Nav active | accent border slide-in (200ms) |
| Message appear | slide-up + fade (300ms ease-out) |
| Chat typing | breathing dots (1s loop) |

---

## 🎯 Demo Content Strategy
**Sidebar Chat History:**
- "Contract Review Session"
- "NDA Template Draft" 
- "Client Consultation Notes"
- "Lease Agreement Analysis"

**Chat Panel Messages:**
- User: "Can you review this employment contract for any concerning clauses?"
- Assistant: "I've reviewed the contract. Here are the key issues I found: [numbered list with legal insights]"
- Show typing indicator for immersion

**Workspace:**
- Replace generic welcome with legal dashboard
- Cards: "Recent Documents", "Pending Reviews", "AI Insights"
- Use real-looking legal document names

---

## 🚀 Implementation Priority
1. **Color palette swap** - Replace harsh blacks with warmer grays
2. **Add rounded corners** - 8-12px throughout
3. **Improve spacing** - 16-24px padding, proper margins
4. **Demo content** - Replace all placeholders
5. **Subtle shadows** - Add depth without being heavy
6. **Typography** - Improve hierarchy and readability

> **Goal**: Transform from amateur to polished in one iteration 