# SkyForge

`SkyForge` is an open-source `python` project designed for `Hypixel Skyblock` players, mainly those interested in making profit in `The Forge` of the `Dwarven Mines`.
This application fetches data from the [Official Hypixel Wiki](https://wiki.hypixel.net/The_Forge) and the [Official Hypixel API](https://api.hypixel.net)
and determines which are the best items to craft for coin profit, based on `Bazaar` and `Auction House` prices.

This tool might be useful to help players fill currently unused forge slots so they can be useful even if the player has no interest in forge items.

## Configuration

Before running the app, you might want to add your preferences and collection levels to the configuration file so the app can determine which items to include in the results. If you don't do this, the app will consider all items in the forge, which might not be ideal for your situation.

Open the [SkyForgeConfigs.json](SkyForgeConfigs.json) file with the text editor of your choice and take a look at the configurations.

- Insert your collection levels into the numbers corresponding to each of the collections. By default, everything is set to max level, so the app will assume you can craft everything.
- Fill in the line for the budget you are willing to invest in coins. The default value is -1, which means no budget limit.
- Insert the table length you want. This is the number of lines the final table will have. For example, if set to `10` (default), the final table will show the 10 best items to forge. Regardless of this number, a `json` will be generated with the full list of best items.
- Fill in the line for the time interval you want in between data refreshes, in seconds. I don't recommend values below two minutes.

## Usage

### Option 1 - Run from Executable (Recommended)

The easiest way to use the app is to simply download the [latest release](https://github.com/Enzo-Nunes/SkyForge/releases/latest)'s executable and config file. Place both files on the same directory and run Skyforge.exe. A terminal window will open with the program.

### Option 2 - Run From Source

Clone the repository:

```bash
git clone https://github.com/Enzo-Nunes/SkyForge.git
cd SkyForge
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Then run the main file:

```bash
python SkyForge.py
```

## Understanding the Data

With the script running, a bunch of info regarding the processing will be shown on the terminal. After all the calculations are done, the program will create the [best_forge_items.json](best_forge_items.json) file with all the relevant data and display a table on the terminal. Both the table and `json` file are sorted by profit per hour.

## Making Coins with the Forge

Once you have chosen an item to invest in, check the recipe on the right and buy the necessary ingredients, either from the `Bazaar` or `Auction House`, and start the crafting process in `The Forge`. If the ingredient is bought from the `Bazaar`, always try creating a `Buy Order`, as it is always cheaper. Naturally, there will be some items which will take forever for their orders to be filled, so you might want to just use `Instant Buy` for those.

Once the forge is complete, sell the item either in the `Bazaar` or `Auction House`. If the item is sold on the `Bazaar`, always try creating a `Sell Order`, as it is always more profitable. Again, there will be some items which will take forever for their orders to be filled, so you might want to just use `Instant Sell` for those.

## Notes and Tips

- Every now and then the program will fetch new data and update its results accordingly. The time between refreshes is configurable, but I don't recomend times under two minutes.
- Maximize the terminal window for clearer results.
- You don't need to close the program to change configurations. Just modify the [configuration file](SkyForgeConfigs.json) and the program will consider this new config the next time it refreshes its data.

## Disclaimer and Friendly Advices

This app might not give perfectly EXACT data, as it fetches its information from the Wiki and API. Use this tool at your own discretion. It's good practice to always check the Auction House and Bazaar for true current prices before investing. Also, this project is neither endorsed by nor affiliated with Hypixel.
