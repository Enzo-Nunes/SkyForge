import json

jsondict = json.loads(open("forge_data.json").read())

items = jsondict["items"]

products = set(items.keys())

ingredients = set(ingredient for details in items.values() for ingredient in details["Recipe"].keys())

both = products & ingredients

# Save to JSON file
with open("both.json", "w") as f:
    json.dump(list(both), f, indent=2)


ingredients_only = ingredients - products

# Save to JSON file
with open("ingredients_only.json", "w") as f:
    json.dump(list(ingredients_only), f, indent=2)
