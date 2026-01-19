# CTR Mapper - Consolidated Transaction Report Mapper

A dual-mode application for processing consolidated transaction reports and generating formatted poliza ledger Excel files.

## 🚀 Features

- **Dual Mode**: Run as web application or desktop application
- **Same Codebase**: Single application with two deployment modes
- **Excel Processing**: Advanced Excel file processing with formula mapping
- **Modern UI**: Vue.js frontend with responsive design
- **Background Processing**: Non-blocking file processing
- **Automatic Cleanup**: Temporary file management

## 📋 Quick Start

### Web Application Mode (Default)
```bash
cd webapp/backend
pip install -r requirements.txt
python app.py
```
Access at: http://localhost:8000

### Desktop Application Mode
```bash
cd webapp/backend
pip install -r requirements.txt
python app.py --desktop
```
Opens automatically in browser at: http://localhost:5000

## 🔧 Build Desktop Executable

### Prerequisites
```bash
cd webapp/backend
pip install -r requirements.txt
pip install pyinstaller
```

### Build Frontend (if not already built)
```bash
cd webapp/frontend-vue
npm install
npm run build
```

### Create Executable
```bash
cd webapp/backend
python build_desktop.py
```

This creates:
- `dist/CTR_Mapper.exe` - Single executable file
- `CTR_Mapper_Desktop_Package/` - Distribution package

## 📁 Project Structure

```
ctr_mapper/
├── script_consolidation_report_mapper.py  # Original Python script
├── webapp/                                 # Web application
│   ├── backend/                           # FastAPI backend
│   │   ├── app.py                         # Main application (dual mode)
│   │   ├── build_desktop.py               # Desktop build script
│   │   ├── services/                      # Processing logic
│   │   ├── models/                        # Data models
│   │   └── requirements.txt               # Dependencies
│   ├── frontend-vue/                      # Vue.js frontend
│   │   ├── src/                           # Source code
│   │   ├── package.json                   # Node dependencies
│   │   └── vite.config.js                 # Build configuration
│   └── frontend-dist/                     # Built frontend files
└── README.md                              # This file
```

## 🎯 Usage

### Input Requirements
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

### Processing Options
- **Header Start Row**: Row number where headers begin (default: 27)
- **Data Start Row**: Row number where data begins (default: 28)
- **Template Header Start**: Output header row (default: 1)
- **Template Data Start**: Output data start row (default: 2)

### Output
The application generates a formatted Excel file with:
- **TC** (Exchange Rate)
- **Nombre** (Transaction Name)
- **divisa** (Currency)
- **GL Account Components**: compania, Unidad, CC, ubicacion, cuenta, subcuenta, equipo, intercompania
- **Financial Data**: debito, credito, debito_convertido, credito_convertido
- **descripcion** (Description)

## 🌐 Deployment Modes

### Web Application - Best For:
- Multiple users in an organization
- Centralized processing and management
- Regular updates and maintenance
- Shared resources and collaboration

### Desktop Application - Best For:
- Individual users or small teams
- Offline processing requirements
- No server infrastructure available
- Client distribution without code exposure

## 📊 API Endpoints

- `GET /`: Main application interface
- `POST /upload`: Upload and process files
- `GET /status/<job_id>`: Check processing status
- `GET /download/<job_id>`: Download processed files
- `GET /health`: Health check (includes mode information)
- `DELETE /cleanup`: Manual cleanup

## 🔒 Security

### Web Mode
- CORS configured for frontend access
- File type validation
- Size limits enforced
- Automatic file cleanup

### Desktop Mode
- All processing done locally
- No network dependencies
- Files automatically cleaned up after 1 hour
- Secure filename generation

## 🛠️ Development

### Frontend Development
```bash
cd webapp/frontend-vue
npm install
npm run dev    # Development server
npm run build  # Production build
```

### Backend Development
```bash
cd webapp/backend
pip install -r requirements.txt
python app.py          # Web mode
python app.py --desktop # Desktop mode
```

## 📦 Dependencies

### Backend
- FastAPI: Web framework
- pandas: Excel processing
- openpyxl: Excel file handling
- uvicorn: ASGI server
- pydantic: Data validation

### Frontend
- Vue.js 3: Frontend framework
- Vite: Build tool
- Modern ES6+ JavaScript

### Build Tools
- PyInstaller: Executable creation
- npm: Node package manager

## 🐛 Troubleshooting

### Common Issues

1. **"No module named 'flask'" error**:
   - Install dependencies: `pip install -r requirements.txt`
   - Use FastAPI version instead of Flask

2. **Frontend not loading**:
   - Build frontend: `cd webapp/frontend-vue && npm run build`
   - Check `frontend-dist/` directory exists

3. **File upload fails**:
   - Verify file format (.xlsx, .xls)
   - Check file size (< 50MB)
   - Ensure required columns exist

4. **Desktop executable won't start**:
   - Check if port 5000 is available
   - Run with administrator privileges if needed
   - Check antivirus software settings

### Development Tips
- Use `python app.py --desktop` for testing desktop mode
- Check console output for detailed error messages
- Monitor uploads/ folder for temporary files
- Use `/health` endpoint to check application status

## 📄 License

This project is proprietary software for Aeromexico consolidation report processing.

## 🆘 Support

For technical support or bug reports, contact your system administrator.