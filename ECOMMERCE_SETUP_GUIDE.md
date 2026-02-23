# E-Commerce Integration Setup Guide

Complete setup guide for Yampi and Appmax integrations in Carbon Helpdesk.

## Files Created

### Core Service Files
1. **backend/app/services/yampi_service.py** (283 lines)
   - Yampi e-commerce API integration
   - Fetches orders by customer email
   - Retrieves order details and tracking info
   - Status normalization to unified format

2. **backend/app/services/appmax_service.py** (275 lines)
   - Appmax payment gateway API integration
   - Fetches sales/transactions by customer email
   - Retrieves sale details and transaction status
   - Status normalization to unified format

### API Router
3. **backend/app/api/ecommerce.py** (292 lines)
   - FastAPI router for ecommerce endpoints
   - Unified order search across both platforms
   - Individual platform endpoints
   - Settings management with credential masking

### Configuration Files
4. **backend/app/config/ecommerce.json**
   - JSON file for storing credentials (as fallback)
   - Structure for Yampi (token, alias) and Appmax (api_key)

5. **backend/app/core/config.py** (UPDATED)
   - Added environment variables:
     - YAMPI_TOKEN
     - YAMPI_ALIAS
     - APPMAX_API_KEY

### Database Migration
6. **backend/migrations/001_ecommerce_settings.sql** (47 lines)
   - Creates `settings` table for key-value config storage
   - Creates `ecommerce_integrations` table for tracking enabled integrations
   - Optional - can use environment variables instead

### Documentation & Examples
7. **backend/ECOMMERCE_INTEGRATION.md**
   - Comprehensive integration documentation
   - API endpoint reference
   - Configuration guide
   - Troubleshooting tips

8. **backend/app/api/ecommerce_examples.py**
   - 7 practical examples of using the API
   - Error handling patterns
   - Batch processing examples

### Main Application
9. **backend/app/main.py** (UPDATED)
   - Added ecommerce router import
   - Registered ecommerce router at /api/ecommerce

## Quick Start

### 1. Set Environment Variables

Add to your `.env` file:

```env
# Yampi Configuration
YAMPI_TOKEN=your_yampi_api_token_here
YAMPI_ALIAS=your_store_alias

# Appmax Configuration
APPMAX_API_KEY=your_appmax_api_key_here
```

### 2. (Optional) Run Database Migration

If you want to use database-backed settings:

```bash
cd /path/to/carbon-helpdesk/backend
psql -U carbon -d carbon_helpdesk < migrations/001_ecommerce_settings.sql
```

### 3. Restart the Application

The FastAPI app will automatically load the new routes:

```bash
# If using Docker
docker-compose restart backend

# If using direct Python
python -m uvicorn app.main:app --reload
```

### 4. Test the API

```bash
# Test unified order search
curl -X GET "http://localhost:8000/api/ecommerce/orders?email=customer@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Test Yampi only
curl -X GET "http://localhost:8000/api/ecommerce/yampi/orders?email=customer@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Test Appmax only
curl -X GET "http://localhost:8000/api/ecommerce/appmax/orders?email=customer@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get settings (credentials masked)
curl -X GET "http://localhost:8000/api/ecommerce/settings" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## API Endpoints Summary

### Base Path: `/api/ecommerce`

#### Unified Endpoints
- `GET /orders?email=X&limit=50` - Search both Yampi and Appmax
- `GET /settings` - Get current configuration (masked credentials)
- `POST /settings?yampi_token=...&yampi_alias=...&appmax_api_key=...` - Update credentials

#### Yampi Endpoints
- `GET /yampi/orders?email=X&limit=50` - Get Yampi orders only
- `GET /yampi/order/{order_id}` - Get order details
- `GET /yampi/order/{order_id}/tracking` - Get tracking info

#### Appmax Endpoints
- `GET /appmax/orders?email=X&limit=50` - Get Appmax sales only
- `GET /appmax/sale/{sale_id}` - Get sale details
- `GET /appmax/transaction/{transaction_id}/status` - Get transaction status

## Unified Order Response Format

All orders are returned in this unified format:

```json
{
  "source": "yampi" | "appmax",
  "order_number": "12345",
  "status": "pago|nao_pago|pendente|cancelado|recusado|abandonado|reembolsado|enviado|entregue",
  "status_label": "Pago",
  "total": 299.90,
  "payment_method": "credit_card" | null,
  "created_at": "2026-02-22T10:30:00Z",
  "tracking_codes": [
    {
      "code": "ABC123XYZ",
      "status": "enviado",
      "url": "https://track.example.com/..."
    }
  ],
  "items": [
    {
      "name": "Product Name",
      "quantity": 1,
      "price": 299.90
    }
  ],
  "raw": {} // Original API response for debugging
}
```

## Status Normalization

Both Yampi and Appmax statuses are normalized to these values:

| Status | Label | Portuguese |
|--------|-------|-----------|
| pago | Paid | Pago |
| nao_pago | Not Paid | Não Pago |
| pendente | Pending | Pendente |
| cancelado | Cancelled | Cancelado |
| recusado | Declined | Recusado |
| abandonado | Abandoned | Abandonado |
| reembolsado | Refunded | Reembolsado |
| enviado | Shipped | Enviado |
| entregue | Delivered | Entregue |

## Configuration Priority

Settings are loaded in this order (first match wins):

1. **Environment Variables** (YAMPI_TOKEN, YAMPI_ALIAS, APPMAX_API_KEY)
2. **JSON File** (backend/app/config/ecommerce.json)
3. **Database** (settings table, if migration was run)

Note: Environment variables are the most secure and recommended method.

## Error Handling

The API gracefully handles various error scenarios:

- **Missing credentials** - Returns `configured: false` with error message
- **Invalid credentials** - Returns HTTP 401 with error message
- **Network errors** - Returns error in JSON response
- **Timeout** - 15-second timeout per request

Example error response:
```json
{
  "configured": false,
  "orders": [],
  "error": "Yampi não configurado (YAMPI_TOKEN e YAMPI_ALIAS)"
}
```

## Security Notes

1. **Credentials are never logged** - API keys/tokens never appear in logs
2. **Masked in responses** - API keys shown as `****...****` in GET /settings
3. **HTTPS only** - All calls to Yampi and Appmax use HTTPS
4. **Authentication required** - All endpoints require valid JWT token
5. **Environment variables** - Recommended way to store secrets

## Performance

- **Request timeout**: 15 seconds per API call
- **Default limit**: 50 orders per source (max 100)
- **No caching**: Fresh data on each request (can be added later)
- **Concurrent requests**: Both sources fetched in parallel in unified endpoint

## Integration with Tickets

### Example: Enrich Ticket Context

```python
# In ticket API handler
from app.services.yampi_service import get_orders_by_email
from app.services.appmax_service import get_orders_by_email as appmax_get

customer_email = ticket.customer.email
yampi_orders = await get_orders_by_email(customer_email)
appmax_orders = await appmax_get(customer_email)

# Add to ticket context
ticket.context['ecommerce_orders'] = {
    'yampi': yampi_orders['orders'],
    'appmax': appmax_orders['orders'],
}
```

## Troubleshooting

### "Yampi não configurado"
- Check `YAMPI_TOKEN` and `YAMPI_ALIAS` in .env
- Verify they're correctly formatted
- Restart the application after changing

### "Chave API Appmax inválida"
- Check `APPMAX_API_KEY` in .env
- Verify it hasn't expired in Appmax dashboard
- Check for whitespace or special characters

### No orders returned
- Verify email exists in the system
- Check API key has read permissions
- Verify test email has actual orders

### Slow responses
- Check network connectivity
- Verify API service status (Yampi/Appmax)
- Consider implementing caching if used frequently

## Future Enhancements

- Implement Redis caching for frequent queries
- Add webhook support for real-time updates
- Store credentials securely in database
- Add bulk order indexing
- Support additional payment gateways
- Order event streaming
- Advanced search and filtering

## Related Documentation

- See `backend/ECOMMERCE_INTEGRATION.md` for full API documentation
- See `backend/app/api/ecommerce_examples.py` for code examples
- See `backend/app/core/config.py` for configuration details

## Support

For issues or questions:
1. Check the troubleshooting section in ECOMMERCE_INTEGRATION.md
2. Review ecommerce_examples.py for usage patterns
3. Check application logs for detailed error messages
4. Verify API credentials with service providers

---

Created: 2026-02-22
Last Updated: 2026-02-22
