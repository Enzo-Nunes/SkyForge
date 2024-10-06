import time
import requests
import json
import pandas

# Colletions and levels
HEART_OF_THE_MOUNTAIN_LEVEL = 5
GEMSTONE_COLLECTION = 4
TUNGSTEN_COLLECTION = 0
UMBER_COLLECTION = 0

# total budget to invest (millions of coins)
BUDGET = 10

BAZAAR_URL = f"https://api.hypixel.net/v2/skyblock/bazaar"
AUCTION_HOUSE_URL = f"https://api.hypixel.net/v2/skyblock/auctions"
HEADERS = {"Content-Type": "application/json"}

bazaar = {}

######################
# Auxiliar Functions #
######################

def is_char_upper(letter: "str") -> "bool":
	return ord("A") <= ord(letter) <= ord("Z")

def is_string_upper(string: "str") -> "bool":
	return all(is_char_upper(letter) for letter in string)

def to_hours(time: "str") -> "float":
	time_quantity, time_type = time.lstrip().split(" ")

	match time_type:
		case "days" | "day":
			return float(time_quantity) * 24
		case "hours" | "hour":
			return float(time_quantity)
		case "minutes" | "minute":
			return float(time_quantity) / 60
		case "seconds" | "second":
			return float(time_quantity) / 3600
	

###################
# Parse Functions #
###################

def parse_name(wiki_name: "str") -> "str":
	
	name_split = wiki_name.split(" ")
	for i in range(len(name_split) - 1, 0, -1):
		if not is_string_upper(name_split[i]):
			break
	
	return " ".join(name_split[:i + 1])

def parse_crafting_time(wiki_time: "str") -> "float":
	return sum(to_hours(time) for time in wiki_time.split(","))

def parse_recipe(wiki_recipe: "str") -> "list[str]":
	# "1 Golden Plate 2 Enchanted Gold Block [] 320 Enchanted Gold [] 51,200 Gold Ingot 5 Glacite Jewel 1 Refined Diamond [] 2 Enchanted Diamond Block [] 320 Enchanted Diamond [] 51,200 Diamond"

	# ["1", "Refined", "Mithril", "160", "Enchanted", "Mithril", "[]", "25,600", "Mithril"]
	recipe_split = wiki_recipe.split(" ")
	recipe = {}

	i = 0
	j = 1
	# Skip the first item because it's the item itself
	while not recipe_split[j].replace(",", "").isnumeric():
		j += 1
	i = j
	j += 1

	while j < len(recipe_split):
		# Get next ingredient
		while j < len(recipe_split) and not recipe_split[j].replace(",", "").isnumeric() and recipe_split[j] != "[]":
			j += 1
		recipe[" ".join(recipe_split[i + 1:j])] = int(recipe_split[i].replace(",", ""))
		i = j
		j += 1

		# Skip recipe tree if needed
		if j < len(recipe_split) and recipe_split[i] == "[]":
			while j < len(recipe_split) and (recipe_split[i] == "[]" or not recipe_split[j].replace(",", "").isnumeric()):
				i += 1
				j += 1
			i += 1
			j += 1
	
	return recipe



##################
# Main Functions #
##################

def get_forge_info() -> "dict[str, dict[str, int | float | dict[str, int]]]":
	"""
	Reads the forge page from the official wiki and parses it to the forge dictionary.

	:return: A dictionary containing the forge item details.
	"""
	FORGE_URL = "https://wiki.hypixel.net/The_Forge"
	WIKI_INDEXES = [5, 12, 24, 42, 70, 82, 100, 114, 125]

	the_forge = {}

	forge_page = pandas.read_html(FORGE_URL)
	item_list = [
		forge_page[i].to_dict(orient="records")[j]
		for i in WIKI_INDEXES
		for j in range(0, len(forge_page[i].to_dict(orient="records")), 2)
	]

	for forge_item in item_list:
		the_forge[parse_name(forge_item["Name & Rarity"])] = {
			"Crafting Time": parse_crafting_time(forge_item["Duration"]),
			"Recipe": parse_recipe(forge_item["Recipe Tree"]),
			# "Requirements": parse_requirements(forge_item["Requirements"]),
		}

	return the_forge


the_forge = get_forge_info()
with open("forge_dict.json", "w") as file:
	json.dump(the_forge, file, indent=4)

# print(parse_recipe("1 Golden Plate 2 Enchanted Gold Block [] 320 Enchanted Gold [] 51,200 Gold Ingot 5 Glacite Jewel 1 Refined Diamond [] 2 Enchanted Diamond Block [] 320 Enchanted Diamond [] 51,200 Diamond"))
# print(parse_recipe("1 Refined Mithril 160 Enchanted Mithril [] 25,600 Mithril"))