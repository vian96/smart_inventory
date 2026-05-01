from typing import List, Dict, Any
from models import Product


def calculate_optimal_restock(products: List[Product], budget: float) -> List[Dict[str, Any]]:
    """
    Алгоритм приоритизации закупок на основе дефицита, цены и риск-фактора категории.
    """
    recommendations = []

    # 1. Фильтруем товары, требующие пополнения
    to_restock = [p for p in products if p.quantity < p.min_stock]

    scored_items = []
    for p in to_restock:
        amount_needed = p.min_stock - p.quantity
        # Чем выше score, тем важнее закупить товар
        priority_score = amount_needed * float(p.price) * p.category.risk_factor

        scored_items.append(
            {
                "product": p,
                "amount_needed": amount_needed,
                "priority_score": priority_score,
                "unit_price": float(p.price),
            }
        )

    # 2. Сортируем по priority_score (убывание)
    scored_items.sort(key=lambda x: x["priority_score"], reverse=True)

    # 3. "Закупаем" в рамках бюджета
    remaining_budget = budget
    for item in scored_items:
        if remaining_budget <= 0:
            break

        p = item["product"]
        total_cost = item["amount_needed"] * item["unit_price"]

        if remaining_budget >= total_cost:
            # Можем закупить всё необходимое количество
            actual_buy = item["amount_needed"]
            cost = total_cost
        else:
            # Закупаем частично на остаток бюджета
            actual_buy = int(remaining_budget // item["unit_price"])
            cost = actual_buy * item["unit_price"]

        if actual_buy > 0:
            recommendations.append(
                {
                    "product_id": p.id,
                    "product_name": p.name,
                    "category_name": p.category.name,
                    "restock_quantity": actual_buy,
                    "estimated_cost": round(cost, 2),
                    "priority_score": round(item["priority_score"], 2),
                }
            )
            remaining_budget -= cost

    return recommendations
