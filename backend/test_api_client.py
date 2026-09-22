import urllib.request
import json

def test_api():
    login_payload = json.dumps({'email': 'admin@fashionstore.com', 'password': 'AdminPassword123!'}).encode('utf-8')
    login_req = urllib.request.Request(
        'http://localhost:8000/api/v1/auth/login',
        data=login_payload,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(login_req) as resp:
        res = json.loads(resp.read().decode())
        token = res['access_token']
        print('Logged in successfully! Roles:', [r['name'] for r in res.get('user', {}).get('roles', [])])

    dash_req = urllib.request.Request(
        'http://localhost:8000/api/v1/analytics/dashboard',
        headers={'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(dash_req) as resp:
        dash = json.loads(resp.read().decode())
        print('\nHTTP 200 OK /api/v1/analytics/dashboard')
        print(f"Total sales revenue: Bs. {dash['total_sales_revenue']:,.2f}")
        print(f"Total orders count: {dash['total_orders_count']}")
        print(f"Average ticket: Bs. {dash['average_ticket']:,.2f}")
        print(f"Sales by channel: {dash['sales_by_channel']}")
        print(f"Sales by branch: {dash['sales_by_branch']}")
        print('Daily sales (last 7 days):')
        for ds in dash['daily_sales_last_7_days']:
            print(f"  {ds['date']}: Bs. {ds['revenue']:,.2f}")

    top_req = urllib.request.Request(
        'http://localhost:8000/api/v1/analytics/reports/top-selling?limit=5',
        headers={'Authorization': f'Bearer {token}'}
    )
    with urllib.request.urlopen(top_req) as resp:
        top = json.loads(resp.read().decode())
        print('\nHTTP 200 OK /api/v1/analytics/reports/top-selling:')
        for t in top:
            print(f" - {t['product_name']} ({t['category_name']}) -> {t['total_units_sold']} uds, Bs. {t['total_revenue']:,.2f}")

if __name__ == '__main__':
    test_api()
