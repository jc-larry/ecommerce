from app.db.session import SessionLocal
from sqlalchemy import text

def consolidate_branches():
    db = SessionLocal()
    try:
        print("--- PASO 1: Migrando referencias de sucursales 3 y 4 a Santa Cruz ---")
        
        # 1. purchase_orders
        po_cnt = db.execute(text("UPDATE purchase_orders SET branch_id = 2 WHERE branch_id IN (3, 4)")).rowcount
        print(f"Purchase orders actualizadas: {po_cnt}")
        
        # 2. inventory_ledger
        il_cnt = db.execute(text("UPDATE inventory_ledger SET branch_id = 2 WHERE branch_id IN (3, 4)")).rowcount
        print(f"Inventory ledger actualizados: {il_cnt}")
        
        # 3. branch_employees
        be_cnt = db.execute(text("DELETE FROM branch_employees WHERE branch_id IN (3, 4)")).rowcount
        print(f"Branch employees eliminados de sucursales 3 y 4: {be_cnt}")
        
        # 4. inventory: consolidar stock en sucursales 1 y 2
        # Obtener inventario de branch 3 y 4
        rows_3_4 = db.execute(text("SELECT branch_id, variant_id, stock_actual, avg_cost, stock_minimo, stock_maximo FROM inventory WHERE branch_id IN (3, 4)")).fetchall()
        print(f"Filas de inventario en sucursales 3 y 4 a consolidar: {len(rows_3_4)}")
        
        for r in rows_3_4:
            target_branch = 1 if r.branch_id == 3 else 2
            # Verificar si ya existe en target_branch
            existing = db.execute(text("SELECT stock_actual FROM inventory WHERE branch_id = :b AND variant_id = :v"), {"b": target_branch, "v": r.variant_id}).fetchone()
            if existing:
                db.execute(text("UPDATE inventory SET stock_actual = stock_actual + :s WHERE branch_id = :b AND variant_id = :v"), {"s": r.stock_actual, "b": target_branch, "v": r.variant_id})
            else:
                db.execute(text("""
                    INSERT INTO inventory (branch_id, variant_id, stock_actual, avg_cost, stock_minimo, stock_maximo, stock_reservado, stock_en_transito)
                    VALUES (:b, :v, :s, :c, :min_s, :max_s, 0, 0)
                """), {"b": target_branch, "v": r.variant_id, "s": r.stock_actual, "c": r.avg_cost, "min_s": r.stock_minimo, "max_s": r.stock_maximo})
                
        del_inv = db.execute(text("DELETE FROM inventory WHERE branch_id IN (3, 4)")).rowcount
        print(f"Inventario de sucursales 3 y 4 removido: {del_inv}")
        
        # 5. Eliminar branches 3 y 4
        del_br = db.execute(text("DELETE FROM branches WHERE id IN (3, 4)")).rowcount
        print(f"Sucursales eliminadas: {del_br}")
        
        # 6. Normalizar y embellecer Sucursales 1 y 2 en Santa Cruz
        db.execute(text("""
            UPDATE branches 
            SET name = 'Sucursal Equipetrol (Santa Cruz)',
                code = 'SCZ-EQUIP',
                city = 'Santa Cruz',
                zone = 'Equipetrol Norte',
                address = 'Av. San Martín esq. Calle 8 #450, Santa Cruz de la Sierra',
                reference = 'Frente a Hotel Los Tajibos',
                phone = '+591 3 3421100',
                whatsapp = '+591 77012345',
                latitude = -17.76840000,
                longitude = -63.19450000,
                is_active = true,
                is_temporarily_closed = false
            WHERE id = 1;
        """))
        
        db.execute(text("""
            UPDATE branches 
            SET name = 'Sucursal Ventura Mall (Santa Cruz)',
                code = 'SCZ-VENTURA',
                city = 'Santa Cruz',
                zone = '4to Anillo / Equipetrol',
                address = 'Av. 4to Anillo esq. Av. San Martín, Centro Comercial Ventura Mall, Nivel 1, Local 142',
                reference = 'Ala Norte frente a escaleras mecánicas',
                phone = '+591 3 3885500',
                whatsapp = '+591 77054321',
                latitude = -17.75480000,
                longitude = -63.19720000,
                is_active = true,
                is_temporarily_closed = false
            WHERE id = 2;
        """))
        
        db.commit()
        print("Consolidación de sucursales completada con éxito.")
        
        # Verificación
        branches = db.execute(text("SELECT id, name, city, address, is_active FROM branches ORDER BY id")).fetchall()
        print(f"\nTotal sucursales en base de datos: {len(branches)}")
        for b in branches:
            print(f"  ID {b.id}: {b.name} | Ciudad: {b.city} | Dirección: {b.address}")
            
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    consolidate_branches()
