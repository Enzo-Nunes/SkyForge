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
			Most ingredients and forged items are only tradeable on one of the two markets. For those, the
			calculator uses whichever price is available. For the items that appear on both, it picks the
			<strong>lower</strong> price as the ingredient cost and the <strong>higher</strong> price as the sell
			value.
		</p>

		<h3>Profit Calculation</h3>
		<p>Items are scored and ranked by <strong>Profit per Hour</strong>:</p>
		<ul>
			<li><strong>Ingredients Cost</strong> = sum of (quantity x cheapest price) for each ingredient.</li>
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
