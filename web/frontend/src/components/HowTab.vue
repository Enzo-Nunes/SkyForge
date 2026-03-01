<template>
	<main class="content-page">
		<h3>Price Sources</h3>
		<p>
			SkyForge gathers its data from two sources: the
			<a href="https://wiki.hypixel.net/The_Forge" target="_blank" rel="noopener">Official Hypixel Wiki</a>,
			which provides forge item recipes, crafting durations and unlock requirements, and the
			<a href="https://api.hypixel.net" target="_blank" rel="noopener">Official Hypixel API</a>, which
			provides live market prices from both the Bazaar and the Auction House.
		</p>
		<p>
			The calculator prioritizes <strong>Bazaar</strong> for pricing. If an item is listed on the Bazaar, that
			price is used; otherwise the Auction House price is used. This is done mainly because trading on the
			<strong>Bazaar</strong> is generally more liquid and consistent.
		</p>
		<p>
			Each row displays a market indicator showing which market was used for the item's sell price. The Recipe
			column also shows indicators for each ingredient, revealing the source of that material's cost.
		</p>

		<h3>Weekly Volume Tracking</h3>
		<p>
			The calculator tracks activity across both markets:
		</p>
		<ul>
			<li><strong>Bazaar Volume</strong> — Taken directly from the Hypixel API's 7-day moving average.</li>
			<li><strong>Auction House Volume</strong> — Tracked by polling the Ended Auctions endpoint every 60 seconds.
				Sales are matched to items using an internal UUID map built during regular price fetches. Only auctions
				with a buyer (BIN) are counted.</li>
		</ul>
		<p>
			The database stores up to 8 days of AH sales polls, automatically pruning older entries. When calculating
			weekly volume, if less than 7 days of data is available, the volume is extrapolated to an estimated 7-day
			projection. The <strong>~</strong> prefix indicates an estimated value; after 7 days of tool uptime, values
			become actual counts.
		</p>

		<h3>Profit Calculation</h3>
		<p>Items are scored and ranked by <strong>Profit per Hour</strong>:</p>
		<ul>
			<li><strong>Ingredients Cost</strong> = sum of (quantity x Bazaar price or AH price if Bazaar unavailable)
				for each ingredient.</li>
			<li><strong>Profit</strong> = Sell Value - Ingredients Cost.</li>
			<li><strong>Profit / hour</strong> = Profit / Duration (hours).</li>
		</ul>

		<h3>Live Updates</h3>
		<p>
			Your browser holds an open WebSocket connection to the web service. Each time the calculator finishes a
			cycle, it posts the new results to the web service, which immediately broadcasts them to every connected
			browser. The status indicator in the top-right corner shows whether your connection is live.
		</p>
	</main>
</template>
