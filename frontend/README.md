# Frontend Quiz Application

A React-based frontend application for an intelligent learning system built with Vite, TypeScript, and Ant Design.

## Tech Stack

- **Build Tool**: Vite 7.x
- **Framework**: React 18.x
- **UI Library**: Ant Design 5.x
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **Testing**: Vitest + React Testing Library + fast-check
- **Language**: TypeScript (strict mode)

## Project Structure

```
src/
├── api/              # API client and endpoint definitions
├── components/       # Reusable UI components
├── pages/            # Page-level components
├── contexts/         # React contexts
├── hooks/            # Custom React hooks
├── types/            # TypeScript type definitions
├── utils/            # Utility functions
└── test/             # Test setup and utilities
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The application will be available at `http://localhost:5173/`

### Build

```bash
npm run build
```

### Testing

```bash
# Run tests once
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui
```

### Linting

```bash
npm run lint
```

## Environment Variables

Create a `.env` file in the root directory:

```
VITE_API_BASE_URL=http://localhost:8000
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm test` - Run tests once
- `npm run test:watch` - Run tests in watch mode
- `npm run test:ui` - Run tests with UI
- `npm run lint` - Lint code

## Features

- User authentication (register/login)
- PDF material upload
- Automatic quiz generation
- Interactive quiz taking
- Detailed grading and feedback
- Mistake book for review
- Responsive design
- Property-based testing

## Development Guidelines

- Follow TypeScript strict mode
- Write both unit tests and property-based tests
- Use Ant Design components for UI consistency
- Keep components small and focused
- Use custom hooks for reusable logic
- Follow the established directory structure
