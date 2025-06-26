# PrivateGPT UI Design Specification

## Overview
PrivateGPT is a dark-themed, professional document intelligence platform that combines chat capabilities with document management. The UI follows a modern, minimalist design language with a focus on usability and visual hierarchy.

## Design System

### Color Palette
- **Background Primary**: `#171717` - Main application background
- **Background Secondary**: `#1F1F1F` - Card/panel backgrounds  
- **Background Tertiary**: `#2A2A2A` - Hover states, selected items
- **Border Default**: `#374151` - All borders and dividers
- **Text Primary**: `#FFFFFF` - Headers and primary text
- **Text Secondary**: `#9CA3AF` - Secondary text and labels
- **Text Tertiary**: `#6B7280` - Muted text and placeholders
- **Accent Primary**: `#6B7280` - Primary buttons and active states
- **Accent Success**: `#10B981` - Success states
- **Accent Warning**: `#F59E0B` - Warning states  
- **Accent Error**: `#EF4444` - Error states
- **Accent Info**: `#3B82F6` - Information states (minimal use)

### Typography
- **Font Family**: System font stack (-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif)
- **Headers**: 
  - H1: 32px, font-weight: 600
  - H2: 24px, font-weight: 600
  - H3: 18px, font-weight: 500
- **Body**: 14px, font-weight: 400
- **Small**: 12px, font-weight: 400
- **Code**: 13px, monospace font family

### Spacing
- Base unit: 4px
- Common spacings: 8px, 16px, 24px, 32px, 48px
- Consistent padding: 16px for cards, 24px for sections

### Border Radius
- Small: 4px (buttons, inputs)
- Medium: 8px (cards, panels)
- Large: 12px (modals)

## Layout Structure

### Main Application Frame
```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar (64px collapsed / 240px expanded)  │  Main Content │
│ ┌─────────┐                                │               │
│ │ Logo    │                                │               │
│ ├─────────┤                                │               │
│ │ Chat    │                                │               │
│ │ Docs    │                                │               │
│ │ Admin   │                                │               │
│ ├─────────┤                                │               │
│ │ User    │                                │               │
│ └─────────┘                                │               │
└─────────────────────────────────────────────────────────────┘
```

### Navigation Sidebar
- **Width**: 64px collapsed, 240px expanded
- **Background**: `#1F1F1F`
- **Border**: 1px solid `#374151` on right
- **Items**:
  - Logo/Brand at top
  - Navigation items with icons + labels
  - Active item: background `#2A2A2A`, left border 3px `#6B7280`
  - Hover: background `#2A2A2A`
  - User profile dropdown at bottom

## Page Layouts

### 1. Chat Interface

#### Layout
```
┌──────────────────────────────────────────────────────────┐
│ Header Bar                                               │
│ ┌──────────────┬────────────────────────────────────────┤
│ │ Conversations│  Chat Messages Area                    │
│ │ Sidebar      │  ┌──────────────────────────────────┐ │
│ │              │  │ System: Welcome message...       │ │
│ │ - Chat 1     │  │                                  │ │
│ │ - Chat 2     │  │ User: Question about...          │ │
│ │ - Chat 3     │  │                                  │ │
│ │              │  │ Assistant: Response with...      │ │
│ │              │  │                                  │ │
│ │              │  └──────────────────────────────────┘ │
│ │              │  ┌──────────────────────────────────┐ │
│ │              │  │ Input area with attachments      │ │
│ └──────────────┴──┴──────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

#### Components

**Conversations Sidebar** (280px wide)
- Search bar at top
- List of conversations with:
  - Title (truncated if too long)
  - Last message preview (gray text)
  - Timestamp
  - Hover state shows edit/delete buttons
- "New Chat" button at top

**Messages Area**
- Messages displayed in bubbles:
  - User messages: Right-aligned, darker background
  - Assistant messages: Left-aligned, slightly lighter background
  - System messages: Centered, muted styling
- Message components:
  - Avatar (user photo or AI icon)
  - Name and timestamp
  - Message content with markdown support
  - Copy button on hover
  - Tool calls shown as collapsible sections

**Input Area**
- Multi-line text input with auto-resize
- Attachment button (paperclip icon)
- Send button (disabled when empty)
- Character/token counter
- Model selector dropdown

### 2. Documents Interface

#### Layout
```
┌────────────────────────────────────────────────────────────┐
│ Documents Header                                           │
│ ┌─────────────┬──────────────┬─────────────────────────────┤
│ │ Collections │ Upload Area  │ Documents Grid             │
│ │ Tree        │              │ ┌─────┐ ┌─────┐ ┌─────┐   │
│ │             │ Drop Zone    │ │Doc 1│ │Doc 2│ │Doc 3│   │
│ │ 📁 Legal    │              │ └─────┘ └─────┘ └─────┘   │
│ │  📂 Contract│ Progress     │ ┌─────┐ ┌─────┐ ┌─────┐   │
│ │ 📁 HR       │ Status       │ │Doc 4│ │Doc 5│ │Doc 6│   │
│ │             │              │ └─────┘ └─────┘ └─────┘   │
│ └─────────────┴──────────────┴─────────────────────────────┤
└────────────────────────────────────────────────────────────┘
```

#### Components

**Collections Sidebar** (320px wide)
- Search bar
- "New Collection" button
- Hierarchical tree view:
  - Expand/collapse arrows
  - Custom emoji icons
  - Folder names with document counts
  - Indentation for hierarchy
  - Drag & drop support
  - Right-click context menu

**Upload Section** (384px wide)
- Drag & drop zone:
  - Dashed border
  - Upload icon
  - "Drag & drop files here or click to browse"
  - Supported formats listed
- Upload progress:
  - File name
  - Progress bar
  - Status (uploading, processing, complete)
  - Processing stages shown

**Documents Grid**
- Card-based layout (3-4 columns)
- Document cards show:
  - File type icon
  - Document title
  - File size
  - Upload date
  - Processing status indicator
  - Hover: Shows action buttons

### 3. Admin Dashboard

#### Layout
```
┌────────────────────────────────────────────────────────────┐
│ Admin Dashboard                                            │
│ ┌────────────┬────────────┬────────────┬────────────┐    │
│ │ Total Users│ Active Today│ Documents  │ Storage    │    │
│ │    156     │     23      │   1,234    │  45.6 GB   │    │
│ └────────────┴────────────┴────────────┴────────────┘    │
│ ┌─────────────────────────────┬───────────────────────┐   │
│ │ User Management Table       │ System Settings       │   │
│ │                             │                       │   │
│ └─────────────────────────────┴───────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

#### Components
- Statistics cards with icons
- Data tables with sorting/filtering
- Settings panels with form controls
- Activity charts and graphs

## Component Library

### Buttons
```
Primary:   [bg-gray-700 hover:bg-gray-600 text-white]
Secondary: [bg-transparent border-gray-600 hover:bg-gray-800]
Danger:    [bg-red-600 hover:bg-red-700 text-white]
Disabled:  [opacity-50 cursor-not-allowed]
```

### Form Controls
- **Text Input**: Dark background, gray border, white text
- **Select**: Custom styled with dropdown arrow
- **Checkbox/Radio**: Custom styled with gray accent
- **Toggle**: iOS-style switch with gray track

### Cards
- Background: `#1F1F1F`
- Border: 1px solid `#374151`
- Border radius: 8px
- Padding: 16px
- Shadow: subtle dark shadow

### Modals
- Overlay: Black with 50% opacity
- Content: Same as cards but centered
- Animation: Fade in with slight scale

### Loading States
- Spinner: Animated circle with gray color
- Skeleton: Animated gray blocks for content
- Progress bars: Gray track with accent fill

## Interactions

### Hover Effects
- Buttons: Lighten background
- Links: Underline
- Cards: Slight elevation/shadow
- List items: Background color change

### Transitions
- All transitions: 200ms ease-in-out
- Hover states: Background/border color
- Accordions: Height with opacity
- Modals: Opacity and scale

### Feedback
- Success: Green toast notification
- Error: Red toast notification  
- Loading: Inline spinners
- Progress: Real-time progress bars

## Responsive Behavior

### Breakpoints
- Mobile: < 640px
- Tablet: 640px - 1024px
- Desktop: > 1024px

### Mobile Adaptations
- Sidebar becomes drawer
- Stack columns vertically
- Larger touch targets (44px min)
- Simplified navigation

## Accessibility

### Requirements
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader labels
- Focus indicators (gray ring)
- Sufficient color contrast

### Focus States
- 2px gray ring around focused elements
- Visible focus on all interactive elements
- Logical tab order

## Special UI Elements

### Code Blocks
- Background: `#0F0F0F`
- Syntax highlighting
- Copy button in top-right
- Line numbers optional

### Data Tables
- Sticky headers
- Sortable columns
- Row hover states
- Pagination controls

### Empty States
- Centered illustration/icon
- Descriptive text
- Action button if applicable

### Error States
- Red border on invalid inputs
- Error message below field
- Form-level error summary

## Animation Guidelines

### Entrance
- Fade in: 200ms
- Slide in: 300ms with ease-out
- Scale in: 200ms from 0.95 to 1

### Loading
- Spinner: Continuous rotation
- Pulse: 2s infinite for skeletons
- Progress: Smooth width transitions

### Feedback
- Button click: Slight scale down
- Success: Check mark animation
- Error: Shake animation

## Implementation Notes

1. **Dark Theme Only**: No light theme option currently
2. **No Blue Colors**: Except for minimal info states
3. **Consistent Spacing**: Use 8px grid system
4. **Performance**: Virtualize long lists
5. **Animations**: Respect prefers-reduced-motion
6. **Icons**: Use Lucide React icon set
7. **Fonts**: System fonts for performance
8. **Images**: Lazy load with blur placeholders