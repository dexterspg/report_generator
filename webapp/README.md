# Excel Consolidation Report Mapper - Web Application

A modern web application for processing consolidated transaction reports and generating formatted poliza ledger Excel files.

## Architecture

- **Backend**: FastAPI (Python)
- **Frontend**: Vue.js 3 with Vite
- **Processing**: pandas, openpyxl
- **File Handling**: Async upload/download with background processing

## Project Structure

```
webapp/
├── backend/
│   ├── app.py                 # FastAPI main application
│   ├── services/
│   │   ├── excel_processor.py # Core Excel processing logic
│   │   └── formula_mapper.py  # Formula functions and mappings
│   ├── models/
│   │   └── schemas.py         # Pydantic data models
│   └── uploads/               # Temporary file storage
├── frontend-vue/
│   ├── src/
│   │   ├── App.vue           # Main Vue component
│   │   ├── main.js           # Vue application entry point
│   │   └── components/       # Vue components
│   ├── package.json          # Node.js dependencies
│   ├── vite.config.js        # Vite configuration
│   └── index.html            # HTML template
├── frontend-dist/            # Built Vue.js files (generated)
├── requirements.txt          # Python dependencies
└── README.md                # This file
```

## Setup Instructions

### 1. Install Backend Dependencies

```bash
cd webapp
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd frontend-vue
npm install
```

### 3. Build Frontend

```bash
npm run build
```

### 4. Run the Application

```bash
cd ../backend
python app.py
```

Or using uvicorn directly:

```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the Application

Open your browser and navigate to:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Development Mode

For development, you can run the Vue.js frontend separately:

```bash
cd frontend-vue
npm run dev
```

This will start the Vue.js development server at http://localhost:3000 with hot reload.

## Features

### Web Interface
- **Drag & Drop Upload**: Easy file upload with visual feedback
- **Progress Tracking**: Real-time processing status with progress bar
- **Advanced Options**: Configurable header and data row positions
- **Responsive Design**: Works on desktop and mobile devices
- **Error Handling**: Clear error messages and retry functionality

### Backend API
- **File Upload**: `/upload` - Upload and process Excel files
- **Status Tracking**: `/status/{job_id}` - Check processing status
- **File Download**: `/download/{job_id}` - Download processed files
- **Health Check**: `/health` - Application health monitoring
- **Cleanup**: `/cleanup` - Manual file cleanup

### Processing Features
- **Background Processing**: Non-blocking file processing
- **Formula Application**: Automatic formula calculations
- **Excel Formatting**: Professional styling with headers and totals
- **GL Account Splitting**: Automatic parsing of account codes
- **Currency Conversion**: Exchange rate calculations
- **Data Validation**: Input validation and error handling

## Usage

1. **Upload File**: Drag and drop or browse for your Excel file
2. **Configure Options**: Set header start row (default: 27) and data start row (default: 28)
3. **Process**: Click "Process File" to start conversion
4. **Monitor Progress**: Watch the progress bar and status updates
5. **Download**: Download the generated poliza ledger file

## Input File Requirements

Your Excel file must contain these columns:
- Translation Type
- Fiscal Year
- Fiscal Period
- Unit
- Contract Name
- Vendor
- GL Account
- Contract Currency
- Amount in Contract Currency

## Output

The application generates a formatted Excel file with:
- **TC** (Exchange Rate)
- **Nombre** (Transaction Name)
- **divisa** (Currency)
- **GL Account Components**: compania, Unidad, CC, ubicacion, cuenta, subcuenta, equipo, intercompania
- **Financial Data**: debito, credito, debito_convertido, credito_convertido
- **descripcion** (Description)

## API Usage

### Upload and Process File

```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@your_file.xlsx" \
     -F "input_header_start=27" \
     -F "input_data_start=28"
```

### Check Status

```bash
curl -X GET "http://localhost:8000/status/{job_id}"
```

### Download Result

```bash
curl -X GET "http://localhost:8000/download/{job_id}" -o result.xlsx
```

## Configuration

### Environment Variables
- `UPLOAD_DIR`: Custom upload directory path
- `MAX_FILE_SIZE`: Maximum file size in bytes (default: 50MB)
- `CLEANUP_INTERVAL`: File cleanup interval in seconds

### Processing Options
- **input_header_start**: Row where headers start (1-indexed)
- **input_data_start**: Row where data starts (1-indexed)
- **template_header_start**: Output header row position
- **template_data_start**: Output data start row position

## Development

### Running in Development Mode

```bash
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Features

1. **Backend**: Add new endpoints in `app.py`
2. **Processing**: Extend `excel_processor.py` or `formula_mapper.py`
3. **Frontend**: Update `app.js` and `styles.css`
4. **Models**: Add new schemas in `schemas.py`

## Deployment

### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

- Use a production ASGI server (gunicorn + uvicorn)
- Set up reverse proxy (nginx)
- Configure SSL/TLS certificates
- Implement proper logging and monitoring
- Set up file storage (S3, etc.) for larger deployments
- Add authentication if required

## Troubleshooting

### Common Issues

1. **File Upload Fails**
   - Check file format (.xlsx, .xls)
   - Verify file size (< 50MB)
   - Ensure required columns exist

2. **Processing Errors**
   - Verify header/data row positions
   - Check for missing or invalid data
   - Review error messages in the UI

3. **Performance Issues**
   - Large files may take longer to process
   - Monitor server resources
   - Consider implementing file size limits

### Logs

Check application logs for detailed error information:
```bash
tail -f app.log
```

## License

This project is proprietary software for Aeromexico consolidation report processing.