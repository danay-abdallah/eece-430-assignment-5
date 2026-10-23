from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from .models import Item


def check_stock(name):
    """Look up how many of an item we have."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    return {"name": item.name, "quantity": item.quantity, "price": str(item.price) if item.price is not None else None}


def list_items():
    """Return every item in the inventory."""
    items = Item.objects.all()
    return {"items": [{"name": i.name, "quantity": i.quantity, "price": str(i.price) if i.price is not None else None} for i in items]}


def add_item(name, quantity):
    """Create a new item, or add to an existing one's stock."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is not None:
        item.quantity += quantity
        item.save()
        return {"name": item.name, "quantity": item.quantity, "created": False}
    item = Item.objects.create(name=name, quantity=quantity)
    return {"name": item.name, "quantity": item.quantity, "created": True}


def remove_stock(name, quantity):
    """Take a quantity out of stock."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    if quantity > item.quantity:
        return {
            "error": f"Cannot remove {quantity}. Only {item.quantity} in stock.",
            "name": item.name,
            "quantity": item.quantity,
        }
    item.quantity -= quantity
    item.save()
    return {"name": item.name, "quantity": item.quantity, "price": str(item.price) if item.price is not None else None}


def delete_item(name):
    """Remove an item from the inventory entirely."""
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    item.delete()
    return {"deleted": name}


TOOL_DECLARATIONS = [
    {
        "type": "function",
        "name": "check_stock",
        "description": "Look up the current quantity of a single item in the inventory. Use this whenever the user asks whether something is in stock or how many there are.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "type": "function",
        "name": "list_items",
        "description": "Return every item in the inventory with its quantity. Use this when the user asks what is in stock generally, or asks for a list, rather than about one specific item.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "add_item",
        "description": "Add stock to the inventory. If the item does not exist it is created; if it already exists the quantity is added to the existing total. Use this for restocking and for new deliveries.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many units to add. Must be positive.",
                },
            },
            "required": ["name", "quantity"],
        },
    },
    {
        "type": "function",
        "name": "remove_stock",
        "description": "Reduce the quantity of an existing item. Use this when items are sold, shipped or used. This does NOT delete the item; it only lowers the number.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the item, e.g. 'Hammer'.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "How many units to remove. Must be positive.",
                },
            },
            "required": ["name", "quantity"],
        },
    },
    {
        "type": "function",
        "name": "delete_item",
        "description": "Permanently remove an item and its record from the inventory entirely. This is destructive. Only use it when the user clearly wants the item gone, not when they want to reduce its quantity.",
        "parameters": {
            "type": "object",
            "properties": {

                "name": {
                    "type": "string",
                    "description": "The name of the item to delete.",
                },
            },
            "required": ["name"],
        },
    },
]

TOOL_FUNCTIONS = {
    "check_stock": check_stock,
    "list_items": list_items,
    "add_item": add_item,
    "remove_stock": remove_stock,
    "delete_item": delete_item,
}


def set_price(name, price):
    """Set a known item's unit price before VAT."""
    try:
        amount = Decimal(str(price))
        if not amount.is_finite() or amount < 0 or amount > Decimal("99999999.99"):
            raise ValueError
        if amount != amount.quantize(Decimal("0.01")):
            raise ValueError
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "Price must be nonnegative, at most 99999999.99, with at most two decimal places."}
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    item.price = amount
    item.save(update_fields=["price"])
    return {"name": item.name, "price": format(amount, ".2f")}


def calculate_cost(name, quantity, vat_percent):
    """Quote a purchase using the stored unit price, without changing stock."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return {"error": "Quantity must be a positive integer."}
    try:
        vat = Decimal(str(vat_percent))
        if not vat.is_finite() or not Decimal("0") <= vat <= Decimal("100"):
            raise ValueError
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "VAT percentage must be a number between 0 and 100."}
    item = Item.objects.filter(name__iexact=name).first()
    if item is None:
        return {"error": f"No item named '{name}' exists in the inventory."}
    if item.price is None:
        return {"error": f"Price for '{item.name}' has not been set. Ask the user for its unit price."}
    subtotal = item.price * quantity
    tax = (subtotal * vat / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "name": item.name, "quantity": quantity,
        "unit_price": format(item.price, ".2f"),
        "subtotal": format(subtotal, ".2f"), "vat_percent": str(vat),
        "vat_amount": format(tax, ".2f"), "total": format(subtotal + tax, ".2f"),
        "stock_available": item.quantity >= quantity,
    }


TOOL_DECLARATIONS.extend([
    {
        "type": "function", "name": "set_price",
        "description": "Set an existing item's unit price before VAT, only when the user supplies a price.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"},
            "price": {"type": "string", "description": "Unit price as a decimal string, e.g. 2.50."},
        }, "required": ["name", "price"]},
    },
    {
        "type": "function", "name": "calculate_cost",
        "description": "Calculate the cost of a positive quantity using the stored price plus the requested VAT percentage. Does not reduce stock.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"},
            "quantity": {"type": "integer"},
            "vat_percent": {"type": "number", "description": "10 means 10 percent; use 0 only if no VAT is requested."},
        }, "required": ["name", "quantity", "vat_percent"]},
    },
])
TOOL_FUNCTIONS.update({"set_price": set_price, "calculate_cost": calculate_cost})
