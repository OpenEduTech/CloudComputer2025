# Frontend Quick Start

You have successfully initialized the frontend application!

## Running the App

Since you are in a dev environment, follow these steps:

1.  Navigate to the directory:
    ```bash
    cd services/web-frontend
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```

3.  Start the development server:
    ```bash
    npm run dev
    ```

4.  Open the browser at the Local URL provided (usually `http://localhost:3000`).

## Features Implemented
- **Mock Data**: The app currently runs on `src/api/index.js` mock data. Search for "熵" to see a rich example. Any other term will show a generic default graph.
- **D3 Graph**: Force-directed graph with zoom, pan, and dragging.
- **Chat Simulation**: Streaming text effect for answers.
