# CTR Mapper Deployment Guide

This guide explains how to deploy and use both versions of the CTR Mapper application.

## Overview

The CTR Mapper project now supports two deployment modes:

1. **Web Application**: Hosted service accessible via web browser
2. **Desktop Application**: Standalone executable for individual users

## Web Application Deployment

### Requirements

- Python 3.8+
- Node.js 16+
- npm or yarn

### Setup

1. **Install Backend Dependencies**:
   ```bash
   cd webapp
   pip install -r requirements.txt
   ```

2. **Install Frontend Dependencies**:
   ```bash
   cd frontend-vue
   npm install
   ```

3. **Build Frontend**:
   ```bash
   npm run build
   ```

4. **Run Application**:
   ```bash
   cd ../backend
   python app.py
   ```

### Access

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Production Deployment

For production, use a proper ASGI server:

```bash
cd webapp/backend
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## Desktop Application Deployment

### For End Users

1. **Download Package**: Get the `CTR_Mapper_Package.zip` file
2. **Extract**: Unzip to your desired location
3. **Run**: Double-click `CTR_Mapper.exe`
4. **Use**: Application opens in your browser automatically

### For Developers

1. **Setup Development Environment**:
   ```bash
   cd desktop
   pip install -r requirements.txt
   ```

2. **Run in Development Mode**:
   ```bash
   python main.py
   ```

3. **Build Executable**:
   ```bash
   python build.py
   ```

## Architecture Comparison

### Web Application
```
webapp/
├── backend/              # FastAPI server
│   ├── app.py
│   ├── services/         # Processing logic
│   └── models/           # Data models
├── frontend-vue/         # Vue.js frontend
│   ├── src/
│   └── dist/             # Built files
└── requirements.txt
```

### Desktop Application
```
desktop/
├── main.py              # Flask server + desktop wrapper
├── services/            # Same processing logic (copied)
├── static/              # Built frontend files (copied)
├── build.py             # PyInstaller build script
└── requirements.txt     # Desktop-specific dependencies
```

## Key Differences

| Feature | Web App | Desktop App |
|---------|---------|-------------|
| **Deployment** | Server hosting required | Standalone executable |
| **Access** | Multiple users via web | Single user per installation |
| **Updates** | Server-side updates | Redistribute executable |
| **Resources** | Shared server resources | Local machine resources |
| **Security** | Network security considerations | Local processing only |
| **Scalability** | High (multiple users) | Low (single user) |

## Use Cases

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

## Maintenance

### Web Application Updates

1. **Backend Changes**:
   ```bash
   cd webapp/backend
   git pull
   # Restart server
   ```

2. **Frontend Changes**:
   ```bash
   cd webapp/frontend-vue
   npm run build
   # Restart server
   ```

### Desktop Application Updates

1. **Make Changes**: Update code in `desktop/` directory
2. **Test**: Run `python main.py` to test changes
3. **Build**: Run `python build.py` to create new executable
4. **Distribute**: Send new executable to users

## Security Considerations

### Web Application
- Implement authentication if needed
- Use HTTPS in production
- Validate all file uploads
- Implement rate limiting
- Regular security updates

### Desktop Application
- Code is compiled but not encrypted
- Local file processing only
- No network security concerns
- Antivirus may flag executable initially

## Performance

### Web Application
- Shared server resources
- Multiple concurrent users
- Database/cache optimization possible
- Network latency considerations

### Desktop Application
- Full local machine resources
- Single user processing
- No network latency
- Limited by local hardware

## Monitoring

### Web Application
- Server logs and monitoring
- User analytics possible
- Performance metrics
- Error tracking

### Desktop Application
- Local console output only
- No centralized monitoring
- User-reported issues only
- Limited debugging capabilities

## Backup and Recovery

### Web Application
- Database backups
- Code repository
- Server configuration
- User data management

### Desktop Application
- Source code repository
- Build artifacts
- User files handled locally
- No centralized backup needed

## Support

### Web Application
- Server-side troubleshooting
- Centralized error handling
- User support via web interface
- System administration required

### Desktop Application
- User-side troubleshooting
- Local error messages
- Individual user support
- No system administration needed

## Migration

### From Web to Desktop
1. Export user data if needed
2. Provide desktop executable
3. User training on new interface
4. Maintain web version during transition

### From Desktop to Web
1. Set up server infrastructure
2. Deploy web application
3. Migrate user workflows
4. Provide web application training

## Conclusion

Both deployment modes serve different needs:

- **Choose Web Application** for organizational deployment with multiple users
- **Choose Desktop Application** for individual users or when server infrastructure is not available

The shared processing logic ensures consistent results regardless of deployment mode.