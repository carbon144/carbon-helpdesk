# Carbon Helpdesk Deployment Script

## Overview
The `fix-all.sh` script is a comprehensive deployment automation tool for the Carbon Helpdesk application. It uses base64 encoding to safely package and deploy application files.

## Files Included

The script decodes and deploys the following base64-encoded files:

### Backend Services
1. **tracking_service.py** - Package tracking via 17track + Correios
   - Location: `/opt/carbon-helpdesk/backend/app/services/tracking_service.py`
   - Supports Correios (Brazil), Cainiao/AliExpress, and 1000+ carriers

2. **notion_service.py** - Notion integration for refunds/cancellations
   - Location: `/opt/carbon-helpdesk/backend/app/services/notion_service.py`
   - Auto-creates Notion database if needed

3. **config.py** - Application configuration
   - Location: `/opt/carbon-helpdesk/backend/app/core/config.py`
   - Contains all API keys and settings references

4. **ecommerce.py** - E-commerce integrations (Shopify, Yampi, Appmaxv)
   - Location: `/opt/carbon-helpdesk/backend/app/api/ecommerce.py`
   - Order fetching and status management

5. **main.py** - FastAPI application entry point
   - Location: `/opt/carbon-helpdesk/backend/app/main.py`
   - CORS configuration, background tasks, routes

### Frontend Pages
6. **TicketDetailPage.jsx** - Detailed ticket view
   - Location: `/opt/carbon-helpdesk/frontend/src/pages/TicketDetailPage.jsx`

7. **TicketsPage.jsx** - Tickets list and management
   - Location: `/opt/carbon-helpdesk/frontend/src/pages/TicketsPage.jsx`

8. **SettingsPage.jsx** - Application settings
   - Location: `/opt/carbon-helpdesk/frontend/src/pages/SettingsPage.jsx`

## Environment Variables

The script automatically sets:

```
TRACK17_API_KEY=2A56C5465474D676CA814D1489E0EA94
NOTION_TOKEN=secret_40SAZxVy68EDOorq70A1O8w8Vcd41e9XBUeHowLJSuE
```

These are saved to `/opt/carbon-helpdesk/.env`

## How to Run

```bash
chmod +x /sessions/inspiring-eloquent-dirac/mnt/carbon-helpdesk/fix-all.sh
/sessions/inspiring-eloquent-dirac/mnt/carbon-helpdesk/fix-all.sh
```

## Script Operations

1. Creates directory structure:
   - `/opt/carbon-helpdesk/backend/app/services/`
   - `/opt/carbon-helpdesk/backend/app/core/`
   - `/opt/carbon-helpdesk/backend/app/api/`
   - `/opt/carbon-helpdesk/frontend/src/pages/`

2. Decodes base64 content using `base64 -d` with heredoc syntax
   - Each file uses a unique delimiter (B64_FILENAME)
   - Safe encoding prevents shell interpretation issues

3. Updates environment configuration
   - Creates/updates `.env` file with API credentials

4. Restarts Docker services:
   - Stops existing containers: `docker compose -f docker-compose.prod.yml down`
   - Rebuilds and starts: `docker compose -f docker-compose.prod.yml up -d --build`

## Safety Features

- Uses `set -e` to exit on errors
- Creates backups of existing `.env` file
- Uses unique base64 delimiters to prevent conflicts
- Validates bash syntax with `-n` flag

## Validation

Script has been validated with:
```bash
bash -n /sessions/inspiring-eloquent-dirac/mnt/carbon-helpdesk/fix-all.sh
# Output: Syntax validation: PASSED
```

## File Details

- **Location**: `/sessions/inspiring-eloquent-dirac/mnt/carbon-helpdesk/fix-all.sh`
- **Size**: 6.8 KB
- **Type**: Bourne-Again shell script
- **Permissions**: Executable (755)

## Troubleshooting

If the script fails:

1. Check Docker is running: `docker ps`
2. Verify directory permissions: `ls -la /opt/carbon-helpdesk/`
3. View Docker logs: `docker logs <container_name>`
4. Check .env file: `cat /opt/carbon-helpdesk/.env`

## Next Steps

After deployment:
1. Verify containers are running: `docker ps`
2. Check application logs: `docker logs carbon-helpdesk-backend`
3. Access the frontend at configured URL
4. Configure additional API keys in settings as needed

