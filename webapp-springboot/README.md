# CTR Mapper - Spring Boot Version

A Spring Boot implementation of the Excel Consolidation Report Mapper web application.

## Architecture

- **Backend**: Spring Boot 3.2 (Java 17)
- **Frontend**: Vue.js 3 with Vite
- **Excel Processing**: Apache POI
- **Build Tool**: Maven

## Project Structure

```
webapp-springboot/
├── backend/
│   ├── src/main/java/com/ctrmapper/
│   │   ├── CtrMapperApplication.java    # Main application
│   │   ├── controller/
│   │   │   ├── CtrMapperController.java # REST API endpoints
│   │   │   └── FrontendController.java  # Static file serving
│   │   ├── service/
│   │   │   ├── ExcelProcessorService.java # Excel processing logic
│   │   │   └── FormulaMapper.java         # Formula calculations
│   │   ├── model/                         # DTOs
│   │   └── config/                        # Configuration classes
│   ├── src/main/resources/
│   │   └── application.properties
│   └── pom.xml
├── frontend-vue/
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/
│   │   └── i18n/
│   ├── package.json
│   └── vite.config.js
└── frontend-dist/                         # Built Vue.js files
```

## Setup Instructions

### Prerequisites

- Java 17 or higher
- Maven 3.8+
- Node.js 18+ and npm

### 1. Install Frontend Dependencies

```bash
cd frontend-vue
npm install
```

### 2. Build Frontend

```bash
npm run build
```

### 3. Build and Run Backend

```bash
cd backend
mvn clean install
mvn spring-boot:run
```

Or run the JAR directly:

```bash
mvn clean package
java -jar target/ctr-mapper-1.0.0.jar
```

### 4. Access the Application

- **Web Interface**: http://localhost:8080
- **API Documentation**: http://localhost:8080/swagger-ui.html (if enabled)

## Development Mode

Run frontend with hot reload:

```bash
cd frontend-vue
npm run dev
```

This starts the Vue.js dev server at http://localhost:3001 with proxy to backend.

## Port Configuration

| Service | Port | Notes |
|---------|------|-------|
| Spring Boot Backend | 8080 | Different from Python (8000) |
| Vue.js Dev Server | 3001 | Different from Python (3000) |

## Running Both Versions Simultaneously

You can run both the Python and Spring Boot versions at the same time:

**Python Version:**
- Backend: http://localhost:8000 (or 5001 in desktop mode)
- Frontend Dev: http://localhost:3000

**Spring Boot Version:**
- Backend: http://localhost:8080
- Frontend Dev: http://localhost:3001

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /upload | Upload and process Excel file |
| GET | /status/{jobId} | Get processing status |
| GET | /download/{jobId} | Download processed file |
| POST | /extract-company-codes | Extract company codes from file |
| GET | /health | Health check |
| DELETE | /cleanup | Clean up old files |

## Features

- Same functionality as Python version
- Async file processing with Spring @Async
- Apache POI for Excel processing
- Vue.js 3 frontend with i18n support
- Company code filtering
- Multiple sheet output by Translation Type
