# Sandbox UI - Complete Visual Interface Specification

## Overview

Sandbox UI is a three-pane legal document workspace that combines ChatGPT's clean sidebar navigation with Cursor's professional tabbed workspace. The interface prioritizes visual clarity, consistent theming, and intuitive navigation for legal document management.

## Overall Layout Structure

### Master Grid Layout
```
┌─────────────┬─────────────────────────────┬─────────────────┐
│   SIDEBAR   │        WORKSPACE            │   AI PANEL      │
│   (Fixed)   │        (Flexible)           │   (Fixed)       │
│   264px     │        Auto-fill            │   320px         │
│   Dark      │        Light                │   Dark          │
└─────────────┴─────────────────────────────┴─────────────────┘
```

**Layout Properties:**
- Total height: 100vh (full viewport)
- No scrollbars on main container
- Grid columns: `[264px 1fr 320px]`
- Zero gaps between panes
- Overflow hidden on main container

## Sidebar (Left Pane) - 264px Width

### Color Scheme
- **Background**: Dark gray (#1f2937 / gray-800)
- **Text**: White (#ffffff)
- **Secondary text**: Light gray (#d1d5db / gray-300)
- **Borders**: Dark gray with transparency (#ffffff20 / white/20)
- **Hover states**: Lighter dark gray (#374151 / gray-700)

### Top Section - Navigation Buttons (Fixed Height)
**Container**: 12px padding on all sides

**Primary Action Button (New Chat)**:
- Full width (240px effective)
- Height: 44px
- Background: Transparent with border
- Border: 1px solid rgba(255,255,255,0.2)
- Rounded corners: 6px
- Text: "New Chat" with MessageSquarePlus icon (16px)
- Icon positioned 12px from left edge
- Text positioned 12px from icon
- Hover: Background becomes rgba(255,255,255,0.1)

**Navigation Buttons** (4px spacing between):
1. Dashboard (LayoutDashboard icon)
2. Documents (FileText icon) 
3. Settings (Settings icon)

Each navigation button:
- Full width (240px effective)
- Height: 40px
- Background: Transparent (hover: rgba(255,255,255,0.05))
- Active state: Background rgba(255,255,255,0.1)
- Text color: #d1d5db (inactive), #ffffff (active)
- Icon: 16px, positioned 12px from left
- Text: 12px from icon
- Rounded corners: 4px

### Separator Line
- Horizontal line across full width (minus 12px margins)
- Color: rgba(255,255,255,0.2)
- Thickness: 1px
- Position: 12px from left/right edges

### Dynamic Content Area (Flexible Height)
**Scrollable container** with 12px top padding

#### Chat Mode Content
**Chat History List**:
- Each item: Full width, height 36px
- Background: Transparent (hover: rgba(255,255,255,0.1))
- Padding: 12px horizontal
- Text: Single line, truncated with ellipsis
- Font size: 14px
- Color: #d1d5db
- 4px spacing between items
- Edit icon (12px) appears on right on hover

#### Documents Mode Content
**File Tree Structure**:
- Folder items with expand/collapse chevrons (12px icons)
- File icons (16px) for documents
- Nested indentation: 16px per level
- Item height: 36px
- Same hover/text styling as chat items
- Expandable folders show/hide children with smooth transition

**File Types Shown**:
- Folders: Folder/FolderOpen icons with chevron right/down
- Documents: FileText icon
- Hierarchy: Contracts, Legal Research folders with nested files

## Workspace (Center Pane) - Flexible Width

### Tab Bar (Fixed Height: 48px)
**Background**: Dark gray (#1f2937 / gray-800)
**Border**: Bottom border 1px solid #374151

#### Individual Tabs
**Inactive Tab**:
- Background: Transparent
- Text color: #d1d5db
- Hover: Background #374151, text #ffffff
- Border right: 1px solid #4b5563
- Padding: 8px horizontal, 8px vertical
- Height: 48px

**Active Tab**:
- Background: White (#ffffff)
- Text color: Dark gray (#111827)
- Border bottom: 2px solid blue (#3b82f6)
- No hover effects

**Tab Content**:
- Icon (16px): FileText for documents, Home for dashboard
- Text: 12px spacing from icon
- Max width: 140px with ellipsis truncation
- Dirty indicator: 4px blue dot if document modified

**Close Button** (per tab):
- 20px × 20px
- Positioned absolute right edge of tab
- X icon (12px)
- Background: White with border and shadow
- Appears only on hover
- Rounded: Full circle

**Add Tab Button**:
- 32px × 32px
- Positioned right edge of tab bar
- Plus icon (16px)
- Colors: #9ca3af (inactive), #ffffff (hover)
- Background on hover: #374151

### Content Area (Flexible Height)
**Background**: Pure white (#ffffff)

#### Dashboard Content
**Container**: 32px padding all sides

**Header Section**:
- Title: "Welcome to Sandbox UI" (24px font, bold, #111827)
- Subtitle: "Your AI-powered legal drafting workspace" (#6b7280)
- 16px spacing between title and subtitle
- 32px spacing below header

**Card Grid**: 3 columns on desktop, equal width with 24px gaps

**Individual Cards**:
- Background: White
- Border: 1px solid #e5e7eb
- Rounded corners: 8px
- Padding: 24px
- Shadow: Subtle drop shadow
- Hover: Slightly elevated shadow

**Card Structure**:
- Header: Icon (20px) + Title (16px font, medium weight)
- 16px spacing below header
- Content area with specific layouts per card type

#### Document Editor Content
**Rich Text Editor** with:
- Toolbar: Multiple formatting buttons in dark theme
- Editor area: White background, prose styling
- Content: Legal document text with proper typography
- Buttons: "Send to Chat", "Save", "Share" in top right

## AI Panel (Right Pane) - 320px Width

### Color Scheme (Matches Sidebar)
- **Background**: Dark gray (#1f2937 / gray-800)
- **Secondary background**: Slightly darker (#374151 / gray-700)
- **Text**: White and light gray
- **Borders**: Dark gray (#374151 / gray-700)

### Header (Fixed Height: 56px)
**Background**: Slightly darker gray (#374151)
**Border**: Bottom 1px solid #374151

**Content**:
- Bot icon (20px, blue #60a5fa) + "AI Assistant" title
- Minimize button (32px) on right with ChevronRight icon
- 16px padding horizontal

### Messages Area (Flexible Height)
**Scrollable container** with 16px padding

**Message Bubbles**:
- User messages: Right-aligned, blue background (#2563eb)
- Assistant messages: Left-aligned, dark gray background (#374151)
- Max width: 75% of container
- Rounded corners: 16px
- Padding: 12px horizontal, 12px vertical
- 16px spacing between messages

**Avatar Circles**:
- 32px diameter
- User: Blue background with User icon
- Assistant: Gray background with Bot icon
- 12px spacing from message bubble

**Loading State**:
- Three bouncing dots animation
- Same styling as assistant message
- Dots: 8px diameter, gray color

### Minimized State
**Width**: 48px
**Background**: Same dark gray
**Content**: Single chevron button centered at top

### Input Area (Fixed Height: ~90px)
**Container**: 16px padding, dark gray background
**Border**: Top 1px solid #374151

**Input Box**:
- Background: #374151 (gray-700)
- Border: 1px solid #4b5563 (gray-600)
- Rounded corners: 8px
- Padding: 12px horizontal, 12px vertical (right padding 48px for button)
- Height: 60px minimum
- Text color: White
- Placeholder: Gray (#9ca3af)

**Send Button**:
- 32px × 32px
- Positioned absolute: 8px from right, 8px from bottom of input
- Background: Blue (#2563eb)
- Rounded: Full circle
- ArrowUp icon (16px, white)
- Disabled state: Gray background (#4b5563), reduced opacity

## Interactive States

### Hover Effects
- **Sidebar buttons**: Background lightens to rgba(255,255,255,0.1)
- **Workspace tabs**: Background changes, text lightens
- **Cards**: Shadow elevation increases
- **Chat input**: Border color brightens

### Active States
- **Sidebar navigation**: Background rgba(255,255,255,0.1), white text
- **Workspace tab**: White background, dark text, blue bottom border
- **Input focus**: Blue border color (#3b82f6)

### Transitions
- All hover states: 150ms ease
- Tab switching: Instant
- Sidebar content switching: Instant
- Message animations: Smooth scroll to bottom

## Typography Scale

- **Large titles**: 24px, bold weight
- **Section headers**: 16px, medium weight  
- **Body text**: 14px, normal weight
- **Small text**: 12px, normal weight
- **Button text**: 14px, medium weight

## Color Palette

### Light Theme (Workspace)
- Background: #ffffff
- Text: #111827, #374151, #6b7280
- Borders: #e5e7eb, #d1d5db
- Interactive: #3b82f6 (blue)

### Dark Theme (Sidebar + AI Panel)
- Background: #1f2937, #374151
- Text: #ffffff, #d1d5db, #9ca3af
- Borders: rgba(255,255,255,0.2), #4b5563
- Interactive: #60a5fa (blue), #2563eb (dark blue)

## Responsive Behavior

### Large Screens (1200px+)
- All panes visible at specified widths
- Card grid: 3 columns

### Medium Screens (768px-1199px)
- Sidebar: Remains 264px
- AI Panel: Remains 320px  
- Workspace: Adjusts to remaining space
- Card grid: 2 columns

### Small Screens (<768px)
- Implementation note: Sidebar and AI panel should become overlays
- Workspace takes full width when others are hidden