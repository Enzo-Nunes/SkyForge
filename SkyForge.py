import time
import requests
import json
import pandas

# heart of the mountain collection level
HEART_OF_THE_MOUNTAIN_LEVEL = 5

# total budget to invest (millions of coins)
BUDGET = 10

api_url = "https://api.hypixel.net/v2"
forge_url = "https://hypixel-skyblock.fandom.com/wiki/The_Forge"
bazaar_url  = f"{api_url}/skyblock/bazaar"
auction_house_url = f"{api_url}/skyblock/auctions"
headers = {"Content-Type": "application/json"}

bazaar = {}
forge = {}

def forge_slots(heart_of_the_mountain_level):
	if heart_of_the_mountain_level < 2:
		return 2
	elif heart_of_the_mountain_level < 8:
		return heart_of_the_mountain_level
	else:
		return 7

api_bazaar = requests.get(bazaar_url, headers=headers).json()
api_auction_house = requests.get(auction_house_url, headers=headers).json()
wiki_forge = pandas.read_html(forge_url)[1].to_dict(orient='records')

def parse_time(time: "str") -> "int":
	time_split = time.split(" ")

	hours = 0
	for index in range(0, len(time_split), 2):
		quantity, time_type = time_split[index], time_split[index + 1]
		match time_type:
			case "Seconds" | "Second":
				hours += float(quantity) / 3600
			case "Minutes" | "Minute":
				hours += float(quantity) / 60
			case "Hours" | "Hour":
				hours += float(quantity)
			case "Days" | "Day":
				hours += float(quantity) * 24
	
	return hours

def parse_cost(wiki_cost: "str") -> "dict[str, int]":
	cost_split = wiki_cost.split("\u00a0")
	cost_split = [y for x in cost_split for y in x.split("\u2009")]
	cost = {}

	for index in range(0, len(cost_split), 2):
		cost[cost_split[index + 1]] = int(cost_split[index].replace(",", "").replace("x", ""))
	
	return cost

def parse_requirements(wiki_requirements: "str") -> "dict[str, int | str]"

for item in wiki_forge:
	forge[item["Name"]] = {
		"Duration": parse_time(item["Duration"]),
		"Materials": parse_cost(item["Cost"]),
		"Requirements": parse_requirements(item["HotM and other Requirements"])
	}


with open("forge_data.json", "w") as forge_file:
    json.dump(forge, forge_file, indent=4)

# while True:



# 	time.sleep(60)