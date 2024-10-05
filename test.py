import pandas
import json

page = pandas.read_html("https://wiki.hypixel.net/The_Forge")

for i, x in enumerate(page):
	page_json = x.to_json(orient="records", indent=4)
	with open(f"forge_wiki/{i}.json", "w") as file:
		file.write(page_json)
		