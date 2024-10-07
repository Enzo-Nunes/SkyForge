# SkyForge
`SkyForge` is a `python` script designed for `Hypixel Skyblock` players, mainly those interested in making profit in `The Forge` of the `Dwarven Mines`.
This application fetches data from the [Official Hypixel Wiki](https://wiki.hypixel.net/The_Forge) and the [Official Hypixel API](https://api.hypixel.net)
and determines which are the best items to craft, based on `Bazaaar` and `Auction House` prices.

# Configuration
Before running the script, you need to add your preferences to the main file. These include you collection levels and the budget you are willing to invest.

Open the `SkyForge.py` file with the text editor of your choice and take a look at the configurations at the beginning of the file. Lines `10-15`

# Installation
1. First of all, clone the repository:
```bash
git clone git@github.com:Enzo-Nunes/SkyForge.git
cd SkyForge
```


2. Install the dependencies in your environment:
```bash
pip install beautifulsoup4 requests roman
```
3. Run the main file:
```bash
python SkyForge.py
```
## Usage
With the script running, a bunch of info will be printed to the terminal. After all calculations are done, a table
