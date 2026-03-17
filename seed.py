import asyncio
from database import connect_db, get_db
from bson import ObjectId


PRODUCTS = [
    {
        "name": "Men Colorblock Slim Fit Crew Neck T-shirt",
        "category": "Men",
        "subcategory": "T-Shirts",
        "technology": "TECHNO COOL+",
        "price": 699,
        "original_price": 999,
        "description": "Stay cool and comfortable with our Colorblock Slim Fit Crew Neck T-shirt featuring TECHNO COOL+ technology for superior moisture management and breathability.",
        "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL"],
        "color": "Blue/Black",
        "rating": 4.5,
        "reviews": 128,
        "tags": ["running", "training", "casual"],
        "in_stock": True,
    },
    {
        "name": "Men Solid Slim Fit Polo T-shirt",
        "category": "Men",
        "subcategory": "T-Shirts",
        "technology": "MATPIQ",
        "price": 799,
        "original_price": 1199,
        "description": "Premium MATPIQ fabric polo that delivers outstanding comfort and durability. Perfect for training or casual wear.",
        "image_url": "https://images.unsplash.com/photo-1586790170083-2f9ceadc732d?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL", "XXL"],
        "color": "Black",
        "rating": 4.3,
        "reviews": 87,
        "tags": ["polo", "casual", "training"],
        "in_stock": True,
    },
    {
        "name": "Men Solid Slim Fit Shorts",
        "category": "Men",
        "subcategory": "Shorts",
        "technology": "TECHNOLITE",
        "price": 599,
        "original_price": 899,
        "description": "Ultra-lightweight TECHNOLITE shorts with 4-way stretch for unrestricted movement during any activity.",
        "image_url": "https://images.unsplash.com/photo-1562183241-b937e95585b6?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL"],
        "color": "Navy",
        "rating": 4.6,
        "reviews": 203,
        "tags": ["running", "training", "shorts"],
        "in_stock": True,
    },
    {
        "name": "Men Solid Slim Fit Trackpants",
        "category": "Men",
        "subcategory": "Trackpants",
        "technology": "ELASTO PLUS",
        "price": 999,
        "original_price": 1499,
        "description": "Performance trackpants with ELASTO PLUS stretch fabric, elasticated waistband and zippered pockets.",
        "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL"],
        "color": "Black",
        "rating": 4.4,
        "reviews": 156,
        "tags": ["trackpants", "running", "casual"],
        "in_stock": True,
    },
    {
        "name": "Women Solid Slim Fit Crew Neck T-shirt",
        "category": "Women",
        "subcategory": "T-Shirts",
        "technology": "TECHNO COOL",
        "price": 649,
        "original_price": 949,
        "description": "Designed for active women, this TECHNO COOL t-shirt offers superior moisture wicking and a flattering slim fit.",
        "image_url": "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=600&auto=format",
        "sizes": ["XS", "S", "M", "L"],
        "color": "Violet",
        "rating": 4.7,
        "reviews": 94,
        "tags": ["yoga", "running", "training"],
        "in_stock": True,
    },
    {
        "name": "Women Solid Regular Fit Shorts",
        "category": "Women",
        "subcategory": "Shorts",
        "technology": "TS FLEXI",
        "price": 549,
        "original_price": 799,
        "description": "Comfortable TS FLEXI shorts with 4-way stretch for yoga, training and daily wear.",
        "image_url": "https://images.unsplash.com/photo-1506629082955-511b1aa562c8?w=600&auto=format",
        "sizes": ["XS", "S", "M", "L"],
        "color": "Black",
        "rating": 4.5,
        "reviews": 71,
        "tags": ["yoga", "shorts", "training"],
        "in_stock": True,
    },
    {
        "name": "Women Relaxed Fit Sports Trackpants",
        "category": "Women",
        "subcategory": "Trackpants",
        "technology": "ELASTO PLUS",
        "price": 899,
        "original_price": 1299,
        "description": "Relaxed fit trackpants with ELASTO PLUS for ultimate comfort during workout or rest.",
        "image_url": "https://images.unsplash.com/photo-1591195853828-11db59a44f43?w=600&auto=format",
        "sizes": ["XS", "S", "M", "L"],
        "color": "Heather Grey",
        "rating": 4.2,
        "reviews": 48,
        "tags": ["trackpants", "casual", "yoga"],
        "in_stock": True,
    },
    {
        "name": "Men Hooded Slim Fit Sweatshirt",
        "category": "Men",
        "subcategory": "Sweatshirts",
        "technology": "TECHNOWARM+",
        "price": 1299,
        "original_price": 1999,
        "description": "Stay warm in our TECHNOWARM+ hoodie with fleece lining and kangaroo pocket.",
        "image_url": "https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL", "XXL"],
        "color": "Olive Green",
        "rating": 4.6,
        "reviews": 312,
        "tags": ["winter", "casual", "hoodie"],
        "in_stock": True,
    },
    {
        "name": "Boys Colorblock Slim Fit Sports T-shirt",
        "category": "Boys",
        "subcategory": "T-Shirts",
        "technology": "TECHNO DRY",
        "price": 449,
        "original_price": 699,
        "description": "Made for active boys, with TECHNO DRY quick-dry technology for sports and outdoor activities.",
        "image_url": "https://images.unsplash.com/photo-1519238263530-99bdd11df2ea?w=600&auto=format",
        "sizes": ["8Y", "10Y", "12Y", "14Y"],
        "color": "Red/Black",
        "rating": 4.4,
        "reviews": 56,
        "tags": ["boys", "sports", "t-shirt"],
        "in_stock": True,
    },
    {
        "name": "Boys Solid Slim Fit Shorts",
        "category": "Boys",
        "subcategory": "Shorts",
        "technology": "TECHNO GUARD",
        "price": 399,
        "original_price": 599,
        "description": "Durable TECHNO GUARD shorts for boys who love sports and active play.",
        "image_url": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=600&auto=format",
        "sizes": ["8Y", "10Y", "12Y", "14Y"],
        "color": "Black",
        "rating": 4.3,
        "reviews": 34,
        "tags": ["boys", "shorts", "sports"],
        "in_stock": True,
    },
    {
        "name": "Men Printed Oversized Round Neck T-shirt",
        "category": "Men",
        "subcategory": "T-Shirts",
        "technology": "ELASTO PLUS",
        "price": 849,
        "original_price": 1299,
        "description": "Trendy oversized fit with bold graphics and ELASTO PLUS stretch for maximum comfort.",
        "image_url": "https://images.unsplash.com/photo-1503342217505-b0a15ec3261c?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL"],
        "color": "Charcoal",
        "rating": 4.5,
        "reviews": 189,
        "tags": ["oversized", "casual", "training"],
        "in_stock": True,
    },
    {
        "name": "Women Slim Fit Sports Bra",
        "category": "Women",
        "subcategory": "Innerwear",
        "technology": "ELASTO PLUS",
        "price": 499,
        "original_price": 799,
        "description": "High-performance sports bra with ELASTO PLUS for superior support during intense workouts.",
        "image_url": "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=600&auto=format",
        "sizes": ["XS", "S", "M", "L"],
        "color": "Black",
        "rating": 4.8,
        "reviews": 267,
        "tags": ["yoga", "training", "sports bra"],
        "in_stock": True,
    },
    {
        "name": "Men Solid Active Out Polo Neck T-shirt",
        "category": "Men",
        "subcategory": "T-Shirts",
        "technology": "COTFLEX",
        "price": 749,
        "original_price": 1099,
        "description": "Classic polo with COTFLEX cotton-blend for a premium feel during sports and casual outings.",
        "image_url": "https://images.unsplash.com/photo-1520175480921-4edfa2983e0f?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL", "XXL"],
        "color": "Deep Pink",
        "rating": 4.2,
        "reviews": 73,
        "tags": ["polo", "casual", "cotflex"],
        "in_stock": True,
    },
    {
        "name": "Men Solid Slim Fit Cargo Joggers",
        "category": "Men",
        "subcategory": "Trackpants",
        "technology": "DURACOOL+",
        "price": 1099,
        "original_price": 1599,
        "description": "Stylish cargo joggers with DURACOOL+ for breathability and multi-pocket utility.",
        "image_url": "https://images.unsplash.com/photo-1509551388413-e18d0ac5d495?w=600&auto=format",
        "sizes": ["S", "M", "L", "XL"],
        "color": "Black",
        "rating": 4.5,
        "reviews": 112,
        "tags": ["joggers", "cargo", "casual"],
        "in_stock": True,
    },
    {
        "name": "Women Jacquard Boxy Fit Round Neck T-shirt",
        "category": "Women",
        "subcategory": "T-Shirts",
        "technology": "DOUBLE COOL",
        "price": 799,
        "original_price": 1199,
        "description": "Trendy jacquard texture with DOUBLE COOL technology for all-day freshness.",
        "image_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=600&auto=format",
        "sizes": ["XS", "S", "M", "L"],
        "color": "Sage Green",
        "rating": 4.6,
        "reviews": 92,
        "tags": ["casual", "boxy", "women"],
        "in_stock": True,
    },
]

FAQS = [
    {
        "question": "What is your return policy?",
        "answer": "We offer a hassle-free 30-day return policy. Items must be unworn, unwashed and in original packaging. To initiate a return, contact our support team with your order ID.",
        "keywords": ["return", "refund", "policy", "exchange", "returns"],
        "category": "Returns",
    },
    {
        "question": "How long does shipping take?",
        "answer": "Standard shipping takes 5-7 business days. Express shipping (2-3 business days) is available at checkout. We offer free shipping on orders above ₹999.",
        "keywords": ["shipping", "delivery", "dispatch", "ship", "when", "arrive"],
        "category": "Shipping",
    },
    {
        "question": "How do I track my order?",
        "answer": "You can track your order by visiting the 'My Orders' section on our website and entering your order ID. You will also receive email updates at every stage.",
        "keywords": ["track", "tracking", "order status", "where", "order"],
        "category": "Orders",
    },
    {
        "question": "What sizes are available?",
        "answer": "We offer sizes XS, S, M, L, XL, and XXL for adults, and age-based sizes (8Y, 10Y, 12Y, 14Y) for boys. Please refer to our size chart on each product page for exact measurements.",
        "keywords": ["size", "sizing", "fit", "measurements", "chart", "small", "medium", "large"],
        "category": "Sizing",
    },
    {
        "question": "Are your products sweat-proof?",
        "answer": "Our products use advanced fabric technologies like TECHNO COOL+, DURACOOL+, and ELASTO PLUS that offer superior moisture management. They are designed to keep you dry and comfortable during intense activity.",
        "keywords": ["sweat", "moisture", "dry", "breathable", "fabric", "technology"],
        "category": "Products",
    },
    {
        "question": "Do you offer Cash on Delivery (COD)?",
        "answer": "Yes! We offer Cash on Delivery across India. COD orders are confirmed via a phone call before dispatch.",
        "keywords": ["cod", "cash", "delivery", "payment", "pay"],
        "category": "Payment",
    },
    {
        "question": "How do I cancel my order?",
        "answer": "Orders can be cancelled within 2 hours of placement if they haven't been dispatched. Contact our support team immediately with your order ID to initiate cancellation.",
        "keywords": ["cancel", "cancellation", "stop order"],
        "category": "Orders",
    },
    {
        "question": "Is there a warranty on products?",
        "answer": "All Technosport products come with a 90-day manufacturing defect warranty. This covers issues like stitching defects or fabric damage under normal use.",
        "keywords": ["warranty", "defect", "guarantee", "quality"],
        "category": "Products",
    },
    {
        "question": "Do you ship outside India?",
        "answer": "Currently we only ship within India. International shipping is coming soon — stay tuned for announcements.",
        "keywords": ["international", "outside india", "global", "abroad", "worldwide"],
        "category": "Shipping",
    },
    {
        "question": "How do I contact customer support?",
        "answer": "You can reach us via this chatbot, email at support@technosport.in, or call us at +91 98765 43210 between 9 AM – 6 PM, Monday to Saturday.",
        "keywords": ["contact", "support", "help", "phone", "email", "reach"],
        "category": "Support",
    },
]


async def seed():
    await connect_db()
    database = get_db()

    # Clear existing data
    await database.products.drop()
    await database.inventory.drop()
    await database.orders.drop()
    await database.order_items.drop()
    await database.invoices.drop()
    await database.faqs.drop()
    await database.feedback.drop()
    print("🗑️  Cleared existing collections")

    # Seed products
    result = await database.products.insert_many(PRODUCTS)
    product_ids = result.inserted_ids
    print(f"✅ Inserted {len(product_ids)} products")

    # Seed inventory
    inventory_docs = []
    for i, product_id in enumerate(product_ids):
        product = PRODUCTS[i]
        for size in product["sizes"]:
            # Randomise stock - some items near low threshold for demo
            quantity = 50 if i % 4 != 0 else 8
            inventory_docs.append({
                "product_id": str(product_id),
                "size": size,
                "quantity": quantity,
                "threshold": 10,
                "vendor": f"Vendor {(i % 3) + 1}",
                "reorder_quantity": 100,
            })
    await database.inventory.insert_many(inventory_docs)
    print(f"✅ Inserted {len(inventory_docs)} inventory records")

    # Seed FAQs
    await database.faqs.insert_many(FAQS)
    print(f"✅ Inserted {len(FAQS)} FAQs")

    # Create indexes
    await database.products.create_index("category")
    await database.products.create_index("name")
    await database.inventory.create_index("product_id")
    await database.orders.create_index("order_id")
    await database.faqs.create_index("keywords")
    print("✅ Created indexes")

    print("\n🎉 Database seeded successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
