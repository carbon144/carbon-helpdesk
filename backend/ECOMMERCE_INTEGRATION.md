# E-commerce Integration API

This document describes the e-commerce integration services for the Carbon Helpdesk project, including Yampi and Appmax API integrations.

## Overview

The e-commerce integration module provides unified API endpoints to:
- Fetch orders/sales from Yampi e-commerce platform
- Fetch transactions from Appmax payment gateway
- Merge results into a unified order format
- Manage API credentials via environment variables or database

## Architecture

### Services

#### 1. Yampi Service (`backend/app/services/yampi_service.py`)
Integrates with the Yampi e-commerce API to fetch customer orders.

**Base URL:** `https://api.dooki.com.br/v2/{alias}/`
**Authentication:** Header `User-Token: {token}`

**Key Functions:**
- `get_orders_by_email(email, limit=50)` - Fetch orders by customer email
- `get_order_details(order_id)` - Fetch detailed order information
- `get_tracking_info(order_id)` - Fetch tracking details for an order

**Status Normalization:**
Yampi statuses are normalized to standard format:
- `pago` → Paid
- `nao_pago` → Not Paid
- `pendente` → Pending
- `cancelado` → Cancelled
- `recusado` → Declined
- `abandonado` → Abandoned
- `reembolsado` → Refunded
- `enviado` → Shipped
- `entregue` → Delivered

#### 2. Appmax Service (`backend/app/services/appmax_service.py`)
Integrates with the Appmax payment gateway API to fetch customer transactions and sales.

**Base URL:** `https://admin.appmax.com.br/api/v3/`
**Authentication:** Query parameter `access-token={key}`

**Key Functions:**
- `get_orders_by_email(email, limit=50)` - Fetch sales/transactions by customer email
- `get_sale_details(sale_id)` - Fetch detailed sale information
- `get_transaction_status(transaction_id)` - Fetch transaction status

**Status Normalization:**
Appmax statuses are normalized to match Yampi format (see above).

### API Router

#### Base Path: `/api/ecommerce`

All endpoints require authentication (JWT token).

##### Unified Endpoints

**GET /ecommerce/orders**
```
Query Parameters:
  - email (required): Customer email
  - limit (optional, default=50): Max results per source

Response:
{
  "customer_email": "customer@example.com",
  "orders": [
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
          "url": "https://track.example.com/ABC123XYZ"
        }
      ],
      "items": [
        {
          "name": "Product Name",
          "quantity": 1,
          "price": 299.90
        }
      ],
      "raw": {} // Original API response
    }
  ],
  "total": 2,
  "sources": {
    "yampi": {
      "configured": true,
      "count": 1,
      "error": null
    },
    "appmax": {
      "configured": true,
      "count": 1,
      "error": null
    }
  }
}
```

**GET /ecommerce/yampi/orders**
Fetch orders from Yampi only.

**GET /ecommerce/appmax/orders**
Fetch orders from Appmax only.

##### Order Details Endpoints

**GET /ecommerce/yampi/order/{order_id}**
Get detailed information about a specific Yampi order.

**GET /ecommerce/yampi/order/{order_id}/tracking**
Get tracking information for a Yampi order.

**GET /ecommerce/appmax/sale/{sale_id}**
Get detailed information about a specific Appmax sale.

**GET /ecommerce/appmax/transaction/{transaction_id}/status**
Get status of a specific Appmax transaction.

##### Configuration Endpoints

**GET /ecommerce/settings**
Get current API configuration (with credentials masked).

```
Response:
{
  "settings": {
    "yampi": {
      "token": "****...****",
      "alias": "store-name"
    },
    "appmax": {
      "api_key": "****...****"
    }
  },
  "sources": {
    "yampi": {
      "configured": true
    },
    "appmax": {
      "configured": false
    }
  }
}
```

**POST /ecommerce/settings**
Update API credentials.

```
Query Parameters (all optional):
  - yampi_token: New Yampi API token
  - yampi_alias: New Yampi store alias
  - appmax_api_key: New Appmax API key

Response: Same as GET /ecommerce/settings
```

## Configuration

### Environment Variables

Add the following to your `.env` file:

```env
# Yampi Configuration
YAMPI_TOKEN=your_yampi_api_token
YAMPI_ALIAS=your_store_alias

# Appmax Configuration
APPMAX_API_KEY=your_appmax_api_key
```

### Application Settings

Settings are read from:
1. **Environment variables** (primary source) - highest priority
2. **JSON file** (`backend/app/config/ecommerce.json`) - fallback
3. **Database** (optional) - via settings table

The JSON file is located at:
```
backend/app/config/ecommerce.json
```

Format:
```json
{
  "yampi": {
    "token": "your_token_here",
    "alias": "your_alias_here"
  },
  "appmax": {
    "api_key": "your_api_key_here"
  }
}
```

## Database Schema

### Optional Tables (created via migration)

Run the migration to create optional database tables:
```sql
psql -U carbon -d carbon_helpdesk < backend/migrations/001_ecommerce_settings.sql
```

This creates:
- `settings` - Key-value store for configuration
- `ecommerce_integrations` - Track enabled integrations and sync status

## Usage Examples

### Get all orders from both sources
```bash
curl -X GET "http://localhost:8000/api/ecommerce/orders?email=customer@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get orders from Yampi only
```bash
curl -X GET "http://localhost:8000/api/ecommerce/yampi/orders?email=customer@example.com" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get tracking info for a Yampi order
```bash
curl -X GET "http://localhost:8000/api/ecommerce/yampi/order/ORDER_ID/tracking" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update API credentials (session-only)
```bash
curl -X POST "http://localhost:8000/api/ecommerce/settings?yampi_token=NEW_TOKEN&yampi_alias=new_alias" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Error Handling

All services include comprehensive error handling:

1. **Configuration errors** - Returns `configured: false` with error message
2. **Network errors** - Logged and returned as JSON error
3. **API errors** - HTTP status codes preserved and detailed
4. **Timeout errors** - 15-second timeout per request

Example error response:
```json
{
  "configured": false,
  "orders": [],
  "error": "Yampi não configurado (YAMPI_TOKEN e YAMPI_ALIAS)"
}
```

## Integration Points

### Ticket Context Enrichment
When viewing a customer ticket, the system can fetch:
- Recent orders and their status
- Payment information from Appmax
- Tracking details for ongoing shipments
- Order history for context

### Status Tracking
Unified status format allows for:
- Consistent status display across integrations
- Automatic customer notifications
- SLA tracking based on order status
- Escalation rules based on order states

## Performance Considerations

- **Request timeout:** 15 seconds per API call
- **Default limit:** 50 orders per source
- **Maximum limit:** 100 orders per query
- **Caching:** Not implemented (fresh data on each request)
- **Rate limiting:** Subject to provider limits

## Security

1. **Credentials masking** - Sensitive keys shown as `****...****` in API responses
2. **Environment variables** - Credentials stored securely in .env
3. **Authentication required** - All endpoints require valid JWT token
4. **HTTPS only** - All API calls to external services use HTTPS
5. **No logging of credentials** - Tokens/keys never logged

## Troubleshooting

### Yampi connection issues
- Verify `YAMPI_TOKEN` and `YAMPI_ALIAS` are correct
- Check token is still valid (tokens can expire)
- Ensure store alias matches your Yampi store

### Appmax connection issues
- Verify `APPMAX_API_KEY` is correct
- Check API key has required permissions
- Verify customer email format is correct

### No orders returned
- Verify customer email matches records in system
- Check API key permissions allow customer email search
- Verify orders exist in source system (not test environment)

## Future Enhancements

- [ ] Webhook support for real-time order updates
- [ ] Caching layer with Redis
- [ ] Database persistence of settings
- [ ] Bulk order fetch and indexing
- [ ] Additional payment gateway integrations
- [ ] Order event streaming
- [ ] Advanced filtering and search
- [ ] Export to CSV/Excel

## Related Files

- Service implementations: `backend/app/services/yampi_service.py`, `appmax_service.py`
- API router: `backend/app/api/ecommerce.py`
- Configuration: `backend/app/core/config.py`
- Database migration: `backend/migrations/001_ecommerce_settings.sql`
- Config file: `backend/app/config/ecommerce.json`
- Main app: `backend/app/main.py` (includes ecommerce router)
