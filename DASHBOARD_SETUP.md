# Dashboard Setup Guide

This guide explains how to set up and run the dashboard functionality that connects the frontend (agentic-sdlc-craft) with the backend (agentic-sdlc).

## Overview

The dashboard has been implemented with the following components:

### Backend (agentic-sdlc)
- **Dashboard API**: `/api/dashboard/` - Complete dashboard data
- **Stats API**: `/api/dashboard/stats` - Project statistics
- **Recent Projects API**: `/api/dashboard/recent-projects` - Recent projects list
- **Projects API**: `/api/projects/` - CRUD operations for projects

### Frontend (agentic-sdlc-craft)
- **Dashboard Component**: Real-time data from backend APIs
- **API Client**: Centralized HTTP client with authentication
- **React Query Hooks**: Data fetching and caching
- **Loading States**: Proper loading and error handling

## Setup Instructions

### 1. Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd agentic-sdlc
   ```

2. Install Python dependencies:
   ```bash
   pip install -r services/api/requirements.txt
   ```

3. Start the backend server:
   ```bash
   cd services/api
   python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`

4. Test the API endpoints:
   ```bash
   python test_dashboard_api.py
   ```

### 2. Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd agentic-sdlc-craft
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create environment configuration:
   Create a `.env.local` file with:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   VITE_DEV_MODE=true
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will be available at `http://localhost:5173`

## API Endpoints

### Dashboard Endpoints

- `GET /api/dashboard/` - Get complete dashboard data (stats + recent projects)
- `GET /api/dashboard/stats` - Get project statistics
- `GET /api/dashboard/recent-projects?limit=10` - Get recent projects

### Project Endpoints

- `GET /api/projects` - List all projects (with filtering and pagination)
- `POST /api/projects` - Create a new project
- `GET /api/projects/{id}` - Get a specific project
- `PUT /api/projects/{id}` - Update a project
- `DELETE /api/projects/{id}` - Delete a project (not yet implemented)

### Response Examples

#### Dashboard Stats
```json
{
  "totalProjects": 5,
  "inDevelopment": 2,
  "completed": 1,
  "teamMembers": 5
}
```

#### Project Summary
```json
{
  "id": "abc123",
  "name": "E-commerce Platform",
  "description": "Modern e-commerce solution",
  "status": "development",
  "progress": 65,
  "stage": "features",
  "createdAt": "2024-01-15",
  "documents": {
    "prd": true,
    "architecture": true,
    "userStories": true,
    "apis": false,
    "plans": true,
    "adr": true
  },
  "currentPlan": {
    "id": "plan1",
    "name": "Core Features Implementation",
    "status": "running",
    "progress": 65,
    "completedTasks": 13,
    "totalTasks": 20,
    "createdAt": "2024-01-16"
  }
}
```

## Features

### Dashboard Features
- **Real-time Statistics**: Total projects, in development, completed, team members
- **Recent Projects**: List of recent projects with progress and status
- **Project Cards**: Each project shows:
  - Name and description
  - Status badge with icon
  - Progress bar
  - Document completion status (PRD, Architecture, Stories, APIs, Plans, ADR)
  - Current plan information (if available)
- **Loading States**: Proper loading indicators and error handling
- **Responsive Design**: Works on desktop and mobile

### Data Flow
1. Frontend loads dashboard data using React Query
2. API client makes HTTP requests to backend
3. Backend queries database for projects, plans, and runs
4. Data is processed and returned as structured JSON
5. Frontend displays data with proper loading and error states

## Troubleshooting

### Backend Issues
- Ensure the database is properly initialized
- Check that all required tables exist (projects, plans, runs)
- Verify the server is running on port 8000
- Check logs for any database connection issues

### Frontend Issues
- Ensure the API base URL is correctly set in environment variables
- Check browser network tab for failed requests
- Verify CORS is properly configured if running on different ports
- Check console for any JavaScript errors

### Common Issues
1. **CORS Errors**: If frontend and backend are on different ports, ensure CORS is configured
2. **Database Connection**: Ensure the SQLite database file exists and is writable
3. **Authentication**: The current implementation uses a simple token-based auth system
4. **Port Conflicts**: Ensure ports 8000 (backend) and 5173 (frontend) are available

## Next Steps

To extend the dashboard functionality:

1. **Add Authentication**: Implement proper user authentication and authorization
2. **Real-time Updates**: Add WebSocket support for real-time dashboard updates
3. **Advanced Filtering**: Add more filtering and sorting options for projects
4. **Charts and Analytics**: Add data visualization components
5. **Project Templates**: Allow users to create projects from templates
6. **Team Management**: Add proper team and user management features

## Development Notes

- The backend uses FastAPI with SQLAlchemy for database operations
- The frontend uses React with TypeScript and Tailwind CSS
- Data fetching is handled by React Query for caching and synchronization
- The API client includes proper error handling and authentication
- All components are fully typed with TypeScript interfaces


