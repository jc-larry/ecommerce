"""
Script de Sembrado y Clasificación por Temporadas de Moda Femenina y Descuentos (CU13).
FashionStore - Sistemas de Información II (Grupo 29)
"""

import sys
from datetime import date, timedelta
from app.db.session import SessionLocal
from app.packages.paquete_catalogo_y_tiendas.models import Season, Product, SeasonalPromotion, Category

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def seed_seasons_and_promotions():
    db = SessionLocal()
    try:
        print("=" * 70)
        print("CONFIGURANDO TEMPORADAS DE MODA FEMENINA Y DESCUENTOS (CU13)")
        print("=" * 70)

        # 1. Definición de las 5 Temporadas de Moda
        seasons_data = [
            {
                "name": "Primavera 2026",
                "start_date": date(2026, 9, 21),
                "end_date": date(2026, 12, 20),
            },
            {
                "name": "Verano 2026 / 2027",
                "start_date": date(2026, 12, 21),
                "end_date": date(2027, 3, 20),
            },
            {
                "name": "Otoño 2026",
                "start_date": date(2026, 3, 21),
                "end_date": date(2026, 6, 20),
            },
            {
                "name": "Invierno 2026",
                "start_date": date(2026, 6, 21),
                "end_date": date(2026, 9, 25),
            },
            {
                "name": "Atemporal / Esenciales",
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
            },
        ]

        seasons_map = {}
        for s_info in seasons_data:
            season = db.query(Season).filter(Season.name == s_info["name"]).first()
            if not season:
                season = Season(
                    name=s_info["name"],
                    start_date=s_info["start_date"],
                    end_date=s_info["end_date"],
                )
                db.add(season)
                db.flush()
                print(f" [+] Creada temporada: {season.name} ({season.start_date} al {season.end_date})")
            else:
                season.start_date = s_info["start_date"]
                season.end_date = s_info["end_date"]
                db.flush()
                print(f" [=] Actualizada temporada: {season.name}")
            seasons_map[s_info["name"]] = season

        # 2. Clasificar las 73 Prendas Existentes
        all_products = db.query(Product).all()
        print(f"\nClasificando {len(all_products)} prendas según estilo, tejido y temporada...")

        counts = {name: 0 for name in seasons_map.keys()}

        for p in all_products:
            text = f"{p.name} {p.description or ''} {p.tags or ''} {p.material or ''}".lower()

            # Reglas heurísticas de moda femenina
            if any(k in text for k in ["abrigo", "saco", "chompa", "suéter", "sweater", "lana", "parka", "térmic", "invierno", "cuello alto", "trench coat grueso"]):
                assigned = seasons_map["Invierno 2026"]
            elif any(k in text for k in ["short", "top corto", "sin manga", "tirante", "lino", "playa", "bikini", "traje de baño", "solera", "fresca", "verano"]):
                assigned = seasons_map["Verano 2026 / 2027"]
            elif any(k in text for k in ["vestido floral", "estampado floral", "falda vaporosa", "primavera", "blusa seda", "blusa ligera", "pastel", "vaporos"]):
                assigned = seasons_map["Primavera 2026"]
            elif any(k in text for k in ["blazer", "cardigan", "palazzo", "pantalón sastre", "camisa manga", "gabardina", "otoño", "terracota", "camel"]):
                assigned = seasons_map["Otoño 2026"]
            elif any(k in text for k in ["jean", "denim", "básico", "básica", "blanco", "negro", "camiseta clásica", "esencial"]):
                assigned = seasons_map["Atemporal / Esenciales"]
            else:
                default_seasons = [
                    seasons_map["Primavera 2026"],
                    seasons_map["Verano 2026 / 2027"],
                    seasons_map["Otoño 2026"],
                    seasons_map["Atemporal / Esenciales"],
                ]
                assigned = default_seasons[p.id % len(default_seasons)]

            p.season_id = assigned.id
            counts[assigned.name] += 1

        db.commit()

        print("\nDistribución de prendas por temporada:")
        for name, count in counts.items():
            print(f"  • {name}: {count} prendas")

        # 3. Campañas y Descuentos de Temporada (CU13)
        print("\nConfigurando Promociones Estacionales Activas (CU13)...")
        today = date.today()

        promotions_to_seed = [
            {
                "name": "🌸 Lanzamiento Primavera: 15% OFF",
                "description": "Descuento especial de bienvenida de primavera en vestidos florales, blusas y faldas ligeras.",
                "discount_percent": 15,
                "season_id": seasons_map["Primavera 2026"].id,
                "start_date": today - timedelta(days=2),
                "end_date": today + timedelta(days=30),
                "is_active": True,
            },
            {
                "name": "❄️ Liquidación Fin de Temporada Invierno: 25% OFF",
                "description": "Precios rebajados en toda la colección de abrigos, chaquetas, suéteres y trench coats de invierno.",
                "discount_percent": 25,
                "season_id": seasons_map["Invierno 2026"].id,
                "start_date": today - timedelta(days=7),
                "end_date": today + timedelta(days=15),
                "is_active": True,
            },
            {
                "name": "☀️ Anticipo Colección Verano: 20% OFF",
                "description": "Reserva o compra antes que nadie las prendas de verano con descuento exclusivo.",
                "discount_percent": 20,
                "season_id": seasons_map["Verano 2026 / 2027"].id,
                "start_date": today - timedelta(days=1),
                "end_date": today + timedelta(days=45),
                "is_active": True,
            },
        ]

        for p_data in promotions_to_seed:
            promo = db.query(SeasonalPromotion).filter(SeasonalPromotion.name == p_data["name"]).first()
            if not promo:
                promo = SeasonalPromotion(
                    name=p_data["name"],
                    description=p_data["description"],
                    discount_percent=p_data["discount_percent"],
                    season_id=p_data["season_id"],
                    category_id=None,
                    start_date=p_data["start_date"],
                    end_date=p_data["end_date"],
                    is_active=p_data["is_active"],
                )
                db.add(promo)
                print(f" [+] Creada campaña: {promo.name} (-{promo.discount_percent}%)")
            else:
                promo.season_id = p_data["season_id"]
                promo.discount_percent = p_data["discount_percent"]
                promo.start_date = p_data["start_date"]
                promo.end_date = p_data["end_date"]
                promo.is_active = p_data["is_active"]
                print(f" [=] Actualizada campaña: {promo.name} (-{promo.discount_percent}%)")

        db.commit()
        print("\n¡Configuración de Temporadas y Promociones completada con éxito!")

    except Exception as e:
        db.rollback()
        print(f"❌ Error durante el sembrado: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_seasons_and_promotions()
