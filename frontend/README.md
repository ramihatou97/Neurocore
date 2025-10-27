# Neurosurgery Knowledge Base - Frontend

React-based frontend application with real-time WebSocket updates for chapter generation and PDF processing.

## Features

### ✅ Complete Backend Parity
- **Authentication**: Login, register, JWT token management
- **Chapter Generation**: Real-time 14-stage generation with WebSocket progress updates
- **PDF Management**: Upload, processing status tracking, image/text extraction
- **Task Monitoring**: Background task progress and status updates
- **Dashboard**: Statistics and recent activity overview

### 🔄 Real-Time Updates
- WebSocket integration for live chapter generation progress
- Real-time task status updates
- Automatic reconnection with exponential backoff
- Heartbeat mechanism for connection health

### 🎨 Modern UI/UX
- Responsive design with Tailwind CSS
- Reusable component library
- Loading states and error handling
- Progress bars and status badges
- Modal dialogs and alerts

## Tech Stack

- **React 18** - UI framework
- **React Router 6** - Client-side routing
- **Axios** - HTTP client with interceptors
- **WebSocket API** - Real-time communication
- **Tailwind CSS** - Utility-first styling
- **Vite** - Build tool and dev server

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client services
│   │   ├── client.js     # Axios instance with auth
│   │   ├── auth.js       # Authentication API
│   │   ├── chapters.js   # Chapters API
│   │   ├── pdfs.js       # PDFs API
│   │   └── tasks.js      # Tasks API
│   ├── components/       # Reusable UI components
│   │   ├── Alert.jsx
│   │   ├── Badge.jsx
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── Input.jsx
│   │   ├── LoadingSpinner.jsx
│   │   ├── Modal.jsx
│   │   ├── Navbar.jsx
│   │   ├── ProgressBar.jsx
│   │   └── ProtectedRoute.jsx
│   ├── contexts/         # React Context providers
│   │   └── AuthContext.jsx
│   ├── hooks/            # Custom React hooks
│   │   └── useWebSocket.js
│   ├── pages/            # Page components
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── Dashboard.jsx
│   │   ├── ChaptersList.jsx
│   │   ├── ChapterCreate.jsx  # Real-time WebSocket updates
│   │   ├── ChapterDetail.jsx
│   │   ├── PDFsList.jsx
│   │   ├── PDFUpload.jsx
│   │   └── TasksList.jsx
│   ├── services/         # Business logic services
│   │   └── websocket.js  # WebSocket client manager
│   ├── utils/            # Utility functions
│   │   ├── constants.js  # App constants
│   │   └── helpers.js    # Helper functions
│   ├── App.jsx           # Main app with routing
│   ├── main.jsx          # Entry point
│   └── index.css         # Global styles
├── .env                  # Environment variables
├── .env.example          # Environment template
├── package.json          # Dependencies
├── tailwind.config.js    # Tailwind configuration
└── vite.config.js        # Vite configuration
```

## Getting Started

### Prerequisites
- Node.js 16+
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API URLs
```

3. Start development server:
```bash
npm run dev
```

4. Build for production:
```bash
npm run build
```

5. Preview production build:
```bash
npm run preview
```

## Environment Variables

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

## Key Features Implementation

### Authentication Flow
- JWT token storage in localStorage
- Automatic token injection via Axios interceptors
- Protected routes with redirect to login
- Token validation on app load

### WebSocket Integration
- Singleton WebSocket client manager
- Connection pooling for multiple channels
- Automatic reconnection with backoff
- Event-driven architecture
- Room-based subscriptions

### Real-Time Chapter Generation
1. User submits topic and type
2. API call initiates generation
3. WebSocket connects to chapter room
4. Receives 14 stage progress updates
5. Displays live progress bar and stage info
6. Redirects to chapter detail on completion

### API Error Handling
- Centralized error parsing
- User-friendly error messages
- Automatic 401 handling with redirect
- Network error detection

## Components

### Core Components
- **ProtectedRoute**: HOC for authentication
- **Navbar**: Main navigation with auth status
- **LoadingSpinner**: Loading indicators
- **ProgressBar**: Progress visualization
- **Badge**: Status badges with colors

### Form Components
- **Input**: Text input with validation
- **Button**: Multiple variants and sizes
- **Modal**: Dialog with backdrop

### Layout Components
- **Card**: Content container
- **Alert**: Notification messages

## Custom Hooks

### useChapterWebSocket
```jsx
const { status, lastMessage, send, isConnected } = useChapterWebSocket(chapterId, {
  onMessage: (data) => {
    // Handle WebSocket messages
  },
});
```

### useAuth
```jsx
const { user, login, logout, isAuthenticated } = useAuth();
```

## Development

### Code Style
- ES6+ JavaScript
- Functional components with hooks
- Tailwind utility classes
- Modular component architecture

### Best Practices
- Single responsibility components
- Custom hooks for reusable logic
- Context for global state
- Proper error boundaries
- Loading and error states

## Performance Optimizations
- Code splitting with React.lazy()
- Memoization for expensive calculations
- Debounced API calls
- WebSocket connection pooling
- Efficient re-render prevention

## Browser Support
- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Future Enhancements
- [ ] Chapter editing with rich text editor
- [ ] Advanced search and filtering
- [ ] User preferences and settings
- [ ] Notification system
- [ ] Dark mode
- [ ] Offline support with service workers
- [ ] Progressive Web App (PWA)

## License
Proprietary - All rights reserved
