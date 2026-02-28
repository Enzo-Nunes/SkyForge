<template>
	<main class="content-page">
		<h3>Reading the Table</h3>
		<p>
			The table defaults to sorting by <strong>Profit / hour</strong> — the most useful metric when you plan to
			collect the item as soon as it's done. Since forge slots are a time-limited resource, a cheaper item
			with a shorter duration might earn more per hour than a more profitable one that ties up your slot for
			several hours.
		</p>
		<p>
			That said, <strong>total Profit</strong> is worth considering too. If you know you'll be away for a
			while — going to sleep, for example — and the forge will finish well before you're back, you may as well
			start an item with higher total profit and a longer duration, even if its Profit / hour is lower. The
			slot would sit idle anyway.
		</p>
		<ul>
			<li>
				<strong>#</strong> — the item's rank by Profit / hour. Always reflects the profit-per-hour order
				regardless of how you sort the table.
			</li>
			<li>
				<strong>Ingredients Cost</strong> — total cost of all required ingredients, using the cheapest
				available source (Bazaar or Auction House).
			</li>
			<li><strong>Sell Value</strong> — best available sell price (Bazaar or Auction House).</li>
			<li><strong>Profit</strong> — Sell Value minus Ingredients Cost.</li>
			<li><strong>Duration</strong> — how long the item takes to forge.</li>
			<li><strong>Profit / hour</strong> — Profit divided by Duration. Used for default ranking.</li>
			<li><strong>Recipe</strong> — ingredients and quantities needed.</li>
		</ul>
		<p>
			Click any numeric column header to sort by that column. Click it again to reverse the order. Sorting by
			<strong>#</strong> and sorting by <strong>Profit / hour</strong> produce the same result.
		</p>

		<h3>Filtering Results</h3>
		<p>The sidebar to the left of the table lets you narrow down which items are shown.</p>
		<ul>
			<li>
				<strong>Collection dropdowns</strong> — set each to your current level. Items that require a higher
				level than yours will be hidden.
			</li>
			<li>
				<strong>Max Cost</strong> — enter the maximum you're willing to spend on ingredients per item. Check
				<em>No budget limit</em> to show all items regardless of cost.
			</li>
		</ul>
		<p>Your filter settings are saved automatically and restored the next time you open the page.</p>

		<h3>Buying Ingredients</h3>
		<p>
			Check the Recipe column for what you need to buy. Most ingredients are only listed on one market —
			either the <strong>Bazaar</strong> or the <strong>Auction House</strong> — so the calculator simply uses
			whichever is available. For the handful of items tradeable on both, it picks the cheaper source, and so
			should you.
		</p>
		<p>
			On the Bazaar, always prefer placing a <strong>Buy Order</strong> over Instant Buy — it is cheaper,
			though it may take time to fill. For fast-moving ingredients or small quantities, Instant Buy is usually
			fine, but be mindful of the difference in price between Buy Orders and Instant Buy.
		</p>

		<h3>Starting the Forge</h3>
		<p>
			Head to <strong>The Forge</strong> in the Dwarven Mines and start the craft. You can queue multiple
			items across different forge slots simultaneously — this tool is especially useful for filling idle
			slots you weren't using anyway.
		</p>

		<h3>Selling the Result</h3>
		<p>
			Once forging completes, sell the item on the <strong>Bazaar</strong> or <strong>Auction House</strong>.
			Most forged items are only tradeable on one of the two, so you'll usually have no choice. For the few
			that appear on both, choose whichever gives you the better sell price.
		</p>
		<p>
			On the Bazaar, always prefer a <strong>Sell Order</strong> over Instant Sell — it yields more, though it
			may sit for a while. It's the same logic of Buy Order vs Instant Buy.
		</p>

		<h3>Disclaimer</h3>
		<p>
			This tool provides estimates based on live market data and wiki information. Prices can change between
			the time you read the table and the time you buy or sell. Use it as a guide, not a guarantee. This
			project is neither endorsed by nor affiliated with Hypixel.
		</p>
	</main>
</template>
