from app.db.session import SessionLocal
from app.packages.paquete_inteligente_y_analitica.routers import (
    get_analytics_dashboard, get_top_selling_products, get_executive_summary_voice
)
from app.packages.paquete_seguridad_usuarios.models import User
from app.packages.paquete_catalogo_y_tiendas.branches.models import Branch

def verify():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == 'admin@fashionstore.com').first()

        # 1. Sucursales
        branches = db.query(Branch).all()
        print('=== SUCURSALES EN SISTEMA ===')
        for b in branches:
            print(f'ID {b.id}: {b.name} | Ciudad: {b.city} | Dirección: {b.address}')

        # 2. Dashboard
        dash = get_analytics_dashboard(db=db, current_user=admin)
        print('\n=== DASHBOARD ANALÍTICO (CU39) ===')
        print(f'Total Recaudación: Bs. {dash.total_sales_revenue:,.2f}')
        print(f'Total Pedidos Pagados: {dash.total_orders_count}')
        print(f'Ticket Promedio: Bs. {dash.average_ticket}')
        print(f'Ventas por Canal: {dash.sales_by_channel}')
        print('Ventas por Sucursal:')
        for sb in dash.sales_by_branch:
            print(f"  - {sb['name']}: Bs. {sb['value']:,.2f}")
        print('Ventas por Categoría:')
        for sc in dash.sales_by_category:
            print(f"  - {sc['name']}: Bs. {sc['value']:,.2f}")
        print('Tendencia Diaria (Últimos 7 días):')
        for ds in dash.daily_sales_last_7_days:
            print(f"  - Fecha {ds['date']}: Bs. {ds['revenue']:,.2f}")

        # 3. Top Selling
        top = get_top_selling_products(limit=8, db=db, current_user=admin)
        print('\n=== PRENDAS MÁS VENDIDAS (CU35) ===')
        for t in top:
            print(f"Prenda #{t.product_id}: {t.product_name} ({t.category_name}) -> {t.total_units_sold} uds vendidas, Recaudación: Bs. {t.total_revenue:,.2f}")

        # 4. Resumen Ejecutivo de Voz
        exec_summary = get_executive_summary_voice(db=db, current_user=admin)
        print('\n=== RESUMEN EJECUTIVO (VOZ) ===')
        print(exec_summary['summary_text'])
    finally:
        db.close()

if __name__ == '__main__':
    verify()
