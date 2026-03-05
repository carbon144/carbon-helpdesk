"""
Examples and test code for the e-commerce integration API.
This file demonstrates how to use the ecommerce services.
"""

import asyncio
from app.services.yampi_service import get_orders_by_email as yampi_get_orders
from app.services.appmax_service import get_orders_by_email as appmax_get_orders


# Example 1: Fetch orders from both sources for a customer
async def example_fetch_all_orders():
    """Fetch orders from both Yampi and Appmax for a customer."""
    email = "customer@example.com"
    
    # Get Yampi orders
    yampi_result = await yampi_get_orders(email)
    print(f"Yampi orders: {yampi_result['total']}")
    for order in yampi_result.get('orders', []):
        print(f"  - Order #{order['order_number']}: {order['status']} - R${order['total']}")
    
    # Get Appmax orders
    appmax_result = await appmax_get_orders(email)
    print(f"Appmax orders: {appmax_result['total']}")
    for order in appmax_result.get('orders', []):
        print(f"  - Order #{order['order_number']}: {order['status']} - R${order['total']}")
    
    # Merge results
    all_orders = yampi_result.get('orders', []) + appmax_result.get('orders', [])
    print(f"Total orders: {len(all_orders)}")


# Example 2: Filter orders by status
async def example_filter_by_status():
    """Get pending orders that need customer follow-up."""
    email = "customer@example.com"
    
    yampi_result = await yampi_get_orders(email)
    appmax_result = await appmax_get_orders(email)
    
    all_orders = yampi_result.get('orders', []) + appmax_result.get('orders', [])
    
    # Filter orders that haven't been delivered yet
    pending_orders = [
        order for order in all_orders 
        if order['status'] not in ['entregue', 'cancelado']
    ]
    
    print(f"Pending orders: {len(pending_orders)}")
    for order in pending_orders:
        tracking = order.get('tracking_codes', [])
        if tracking:
            print(f"  - {order['order_number']}: {order['status']} - Tracking: {tracking[0]['code']}")
        else:
            print(f"  - {order['order_number']}: {order['status']} - No tracking yet")


# Example 3: Get orders with tracking information
async def example_tracking_info():
    """Get orders with tracking details."""
    from app.services.yampi_service import get_tracking_info
    
    email = "customer@example.com"
    
    yampi_result = await yampi_get_orders(email)
    
    for order in yampi_result.get('orders', []):
        order_id = order['order_number']
        
        # Get detailed tracking info
        tracking = await get_tracking_info(order_id)
        
        if 'tracking_codes' in tracking:
            print(f"Order {order_id}:")
            for code in tracking['tracking_codes']:
                print(f"  - {code['code']}: {code['status']}")
                if code.get('url'):
                    print(f"    URL: {code['url']}")


# Example 4: Handle errors gracefully
async def example_error_handling():
    """Demonstrate error handling."""
    # Try with invalid email
    result = await yampi_get_orders("invalid-email")
    
    if not result.get('configured'):
        print(f"Error: {result['error']}")
    else:
        print(f"Found {result['total']} orders")


# Example 5: Batch process multiple customers
async def example_batch_process():
    """Process multiple customers at once."""
    customers = [
        "customer1@example.com",
        "customer2@example.com",
        "customer3@example.com",
    ]
    
    results = {}
    
    for email in customers:
        yampi_result = await yampi_get_orders(email)
        appmax_result = await appmax_get_orders(email)
        
        results[email] = {
            'yampi_count': yampi_result.get('total', 0),
            'appmax_count': appmax_result.get('total', 0),
            'total': (yampi_result.get('total', 0) + appmax_result.get('total', 0)),
        }
    
    print("Batch results:")
    for email, data in results.items():
        print(f"  {email}: {data['total']} total orders")


# Example 6: Generate summary report
async def example_summary_report():
    """Generate a summary of orders by status."""
    email = "customer@example.com"
    
    yampi_result = await yampi_get_orders(email)
    appmax_result = await appmax_get_orders(email)
    
    all_orders = yampi_result.get('orders', []) + appmax_result.get('orders', [])
    
    # Count by status
    status_counts = {}
    total_value = 0.0
    
    for order in all_orders:
        status = order['status_label']
        status_counts[status] = status_counts.get(status, 0) + 1
        total_value += order.get('total', 0)
    
    print(f"Customer: {email}")
    print(f"Total Orders: {len(all_orders)}")
    print(f"Total Value: R${total_value:.2f}")
    print("\nOrders by Status:")
    for status, count in sorted(status_counts.items()):
        print(f"  - {status}: {count}")


# Example 7: Find orders that need attention
async def example_orders_needing_attention():
    """Find orders with issues or long delivery times."""
    email = "customer@example.com"
    
    yampi_result = await yampi_get_orders(email)
    appmax_result = await appmax_get_orders(email)
    
    all_orders = yampi_result.get('orders', []) + appmax_result.get('orders', [])
    
    # Find problematic orders
    issues = []
    
    for order in all_orders:
        if order['status'] == 'recusado':
            issues.append({
                'order': order['order_number'],
                'issue': 'Payment declined',
                'source': order['source'],
            })
        elif order['status'] == 'cancelado':
            issues.append({
                'order': order['order_number'],
                'issue': 'Order cancelled',
                'source': order['source'],
            })
        elif order['status'] == 'enviado' and not order.get('tracking_codes'):
            issues.append({
                'order': order['order_number'],
                'issue': 'No tracking info available',
                'source': order['source'],
            })
    
    print(f"Orders needing attention: {len(issues)}")
    for issue in issues:
        print(f"  - {issue['order']} ({issue['source']}): {issue['issue']}")


# Run examples (for testing)
if __name__ == "__main__":
    print("=== Example 1: Fetch all orders ===")
    asyncio.run(example_fetch_all_orders())
    
    print("\n=== Example 2: Filter by status ===")
    asyncio.run(example_filter_by_status())
    
    print("\n=== Example 3: Tracking info ===")
    asyncio.run(example_tracking_info())
    
    print("\n=== Example 4: Error handling ===")
    asyncio.run(example_error_handling())
    
    print("\n=== Example 5: Batch process ===")
    asyncio.run(example_batch_process())
    
    print("\n=== Example 6: Summary report ===")
    asyncio.run(example_summary_report())
    
    print("\n=== Example 7: Issues found ===")
    asyncio.run(example_orders_needing_attention())
