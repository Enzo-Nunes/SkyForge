import pandas
import json

page = pandas.read_html("https://wiki.hypixel.net/Drill_Motor")

for i, x in enumerate(page):
	page_json = x.to_json(indent=4)
	with open(f"test/{i}.json", "w") as file:
		file.write(page_json)
		