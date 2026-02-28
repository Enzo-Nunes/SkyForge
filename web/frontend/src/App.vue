<template>
    <div class="app">
        <header>
            <div class="header-left">
                <h1>⚒ SkyForge</h1>
                <span class="subtitle">Hypixel Skyblock Forge Profit Tracker</span>
            </div>
            <div class="header-right">
                <span class="updated" v-if="lastUpdated">Updated {{ lastUpdated }}</span>
                <span class="status" :class="status">{{ statusLabel }}</span>
            </div>
        </header>

        <nav class="tabs">
            <button :class="{ active: tab === 'tracker' }" @click="tab = 'tracker'">Tracker</button>
            <button :class="{ active: tab === 'guide' }" @click="tab = 'guide'">Guide</button>
            <button :class="{ active: tab === 'how' }" @click="tab = 'how'">How does it work?</button>
        </nav>

        <main v-if="tab === 'tracker'" class="tracker-layout">
            <aside class="filter-panel">
                <div class="filter-grid">
                    <label v-for="(max, key) in REQUIREMENTS" :key="key" class="filter-field">
                        <span class="filter-label">{{ key }}</span>
                        <div class="filter-controls">
                            <select v-model.number="myLevels[key]">
                                <option v-for="n in max + 1" :key="n - 1" :value="n - 1">{{ n - 1 }}</option>
                            </select>
                            <span class="filter-max">/ {{ max }}</span>
                        </div>
                    </label>
                    <div class="filter-field">
                        <span class="filter-label">Max Cost</span>
                        <div class="filter-controls">
                            <input class="cost-input" type="number" min="0" v-model.number="maxCost"
                                :disabled="noBudget" />
                            <span class="filter-max">coins</span>
                        </div>
                        <label class="no-budget-label">
                            <input type="checkbox" v-model="noBudget" />
                            No budget limit
                        </label>
                    </div>
                </div>
                <button class="filter-reset" @click="resetFilters">Reset</button>
            </aside>

            <div class="tracker-content">
                <div class="waiting" v-if="profits.length === 0">
                    <div class="spinner"></div>
                    <p>Waiting for calculator results…</p>
                </div>

                <div class="table-wrap" v-else>
                    <table>
                        <thead>
                            <tr>
                                <th class="sortable" :class="sortClass('Rank')" @click="sortBy('Rank')">
                                    # <span class="sort-arrow">{{ sortArrow("Rank") }}</span>
                                </th>
                                <th>Item</th>
                                <th class="sortable" :class="sortClass('Cost')" @click="sortBy('Cost')">
                                    Recipe Cost <span class="sort-arrow">{{ sortArrow("Cost") }}</span>
                                </th>
                                <th class="sortable" :class="sortClass('Sell Value')" @click="sortBy('Sell Value')">
                                    Sell Value <span class="sort-arrow">{{ sortArrow("Sell Value") }}</span>
                                </th>
                                <th class="sortable" :class="sortClass('Profit')" @click="sortBy('Profit')">
                                    Profit <span class="sort-arrow">{{ sortArrow("Profit") }}</span>
                                </th>
                                <th class="sortable" :class="sortClass('Duration')" @click="sortBy('Duration')">
                                    Duration <span class="sort-arrow">{{ sortArrow("Duration") }}</span>
                                </th>
                                <th class="sortable" :class="sortClass('Profit per Hour')"
                                    @click="sortBy('Profit per Hour')">
                                    Profit / hour <span class="sort-arrow">{{ sortArrow("Profit per Hour") }}</span>
                                </th>
                                <th>Recipe</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="item in profitsSorted.slice(0, visibleCount)" :key="item.Rank"
                                :class="{ top3: item.Rank <= 3 }">
                                <td class="rank">
                                    <span class="badge" :class="'rank-' + item.Rank">{{ item.Rank }}</span>
                                </td>
                                <td class="name">{{ item.Name }}</td>
                                <td class="number cost">{{ fmt(item.Cost) }}</td>
                                <td class="number sell">{{ fmt(item["Sell Value"]) }}</td>
                                <td class="number profit">+{{ fmt(item.Profit) }}</td>
                                <td class="number">{{ fmtDuration(item.Duration) }}</td>
                                <td class="number pph">{{ fmt(item["Profit per Hour"]) }}</td>
                                <td class="recipe">
                                    <span v-for="(qty, mat) in item.Recipe" :key="mat" class="ingredient">
                                        {{ qty }}x {{ mat }}
                                    </span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    <div class="load-more" v-if="visibleCount < profitsSorted.length">
                        <button @click="visibleCount += 10">
                            Load 10 more ({{ profitsSorted.length - visibleCount }} remaining)
                        </button>
                    </div>
                </div>
            </div>
        </main>

        <main v-else-if="tab === 'guide'" class="content-page">
            <h3>Reading the Table</h3>
            <p>
                The table defaults to sorting by <strong>Profit / hour</strong> — the most useful metric when you plan
                to collect the item as soon as it's done. Since forge slots are a time-limited resource, a cheaper item
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
                    <strong>Ingredients Cost</strong> — total cost in coins of all required ingredients, using the
                    cheapest available source (Bazaar or Auction House).
                </li>
                <li><strong>Sell Value</strong> — best available sell price in coins (Bazaar or Auction House).</li>
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
                    <strong>Max Cost</strong> — enter the maximum amount of coins you're willing to spend on ingredients
                    per item. Check <em>No budget limit</em> to show all items regardless of cost.
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
                On the Bazaar, prefer placing a <strong>Buy Order</strong> over Instant Buy — it is cheaper,
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
                On the Bazaar, prefer placing a <strong>Sell Order</strong> over Instant Sell — it yields more, though it
                may sit for a while. It's the same logic of Buy Order vs Instant Buy.
            </p>

            <h3>Disclaimer</h3>
            <p>
                This tool provides estimates based on live market data and wiki information. Prices can change between
                the time you read the table and the time you buy or sell. Use it as a guide, not a guarantee. This
                project is neither endorsed by nor affiliated with Hypixel.
            </p>
        </main>

        <main v-else-if="tab === 'how'" class="content-page">
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
                <li><strong>Ingredients Cost</strong> = sum of (quantity x cheapest price in coins) for each ingredient.
                </li>
                <li><strong>Profit</strong> = Sell Value in coins - Ingredients Cost.</li>
                <li><strong>Duration</strong> = Crafting duration in hours.</li>
                <li><strong>Profit / hour</strong> = Profit / Duration.</li>
            </ul>

            <h3>Live Updates</h3>
            <p>
                Your browser holds an open WebSocket connection to the web service. Each time the calculator finishes a
                cycle, it posts the new results to the web service, which immediately broadcasts them to every connected
                browser. The status indicator in the top-right corner shows whether your connection is live.
            </p>
        </main>
    </div>

    <footer>
        <a href="https://github.com/Enzo-Nunes/SkyForge" target="_blank" rel="noopener" class="footer-link">
            <svg class="github-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path
                    d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
            Made with 💜 by Enzo
        </a>
    </footer>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted, computed } from "vue";

const profits = ref([]);
const status = ref("connecting");
const lastUpdated = ref(null);
const visibleCount = ref(10);
const tab = ref("tracker");

const REQUIREMENTS = {
    "Heart of the Mountain Tier": 10,
    "Gemstone Collection": 11,
    "Tungsten Collection": 9,
    "Umber Collection": 9,
    "Glacite Collection": 9,
    "Hard Stone Collection": 7,
};

const savedLevels = JSON.parse(localStorage.getItem("skyforge_levels") || "null");
const myLevels = reactive(savedLevels || Object.fromEntries(Object.entries(REQUIREMENTS).map(([k, v]) => [k, v])));
const maxCost = ref(parseInt(localStorage.getItem("skyforge_maxCost") || "-1"));
const noBudget = ref(maxCost.value === -1);

watch(noBudget, (val) => {
    if (val) {
        maxCost.value = -1;
    } else if (maxCost.value < 0) {
        maxCost.value = 0;
    }
});

const profitsFiltered = computed(() =>
    profits.value.filter((item) => {
        if (maxCost.value > 0 && item.Cost > maxCost.value) return false;
        for (const [req, level] of Object.entries(item.Requirements || {})) {
            if ((myLevels[req] ?? REQUIREMENTS[req] ?? 0) < level) return false;
        }
        return true;
    }),
);

const sortKey = ref("Profit per Hour");
const sortDir = ref("desc");

function sortBy(key) {
    if (sortKey.value === key) {
        sortDir.value = sortDir.value === "desc" ? "asc" : "desc";
    } else {
        sortKey.value = key;
        sortDir.value = key === "Cost" || key === "Duration" || key === "Rank" ? "asc" : "desc";
    }
    visibleCount.value = 10;
}

function sortClass(key) {
    return { active: sortKey.value === key, asc: sortKey.value === key && sortDir.value === "asc" };
}

function sortArrow(key) {
    if (sortKey.value !== key) return "↕";
    return sortDir.value === "desc" ? "↓" : "↑";
}

const profitsSorted = computed(() => {
    const key = sortKey.value;
    const dir = sortDir.value === "desc" ? -1 : 1;
    return [...profitsFiltered.value].sort((a, b) => {
        const av = a[key] ?? 0;
        const bv = b[key] ?? 0;
        return (av < bv ? -1 : av > bv ? 1 : 0) * dir;
    });
});

function resetFilters() {
    for (const [key, max] of Object.entries(REQUIREMENTS)) {
        myLevels[key] = max;
    }
    maxCost.value = -1;
}

watch(myLevels, () => {
    localStorage.setItem("skyforge_levels", JSON.stringify({ ...myLevels }));
    visibleCount.value = 10;
});

watch(maxCost, (val) => {
    localStorage.setItem("skyforge_maxCost", String(val));
    visibleCount.value = 10;
});

const statusLabel = computed(
    () =>
        ({
            connecting: "Connecting…",
            connected: "Live",
            disconnected: "Disconnected",
            offline: "Offline",
        })[status.value],
);

const fmt = (n) => Number(n).toLocaleString("en-US");

const fmtDuration = (hours) => {
    const totalSeconds = Math.round(hours * 3600);
    const d = Math.floor(totalSeconds / 86400);
    const h = Math.floor((totalSeconds % 86400) / 3600);
    const m = Math.floor((totalSeconds % 3600) / 60);
    const s = totalSeconds % 60;
    if (d > 0) return m > 0 ? `${d}d ${h}h ${m}m` : h > 0 ? `${d}d ${h}h` : `${d}d`;
    if (h > 0) return m > 0 ? `${h}h ${m}m` : `${h}h`;
    if (m > 0) return s > 0 ? `${m}m ${s}s` : `${m}m`;
    return `${s}s`;
};

let ws = null;
let reconnectTimer = null;
let intentionalClose = false;

function connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws`);

    ws.onopen = () => {
        status.value = "connected";
        clearTimeout(reconnectTimer);
    };

    ws.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data?.profits) {
            profits.value = data.profits;
            visibleCount.value = 10;
            lastUpdated.value = new Date(data.calculated_at).toLocaleTimeString(undefined, { timeZoneName: "short" });
        } else if (data?.type === "shutdown") {
            intentionalClose = true;
            status.value = "offline";
        }
        // ignore ping objects
    };

    ws.onclose = () => {
        if (intentionalClose) return;
        status.value = "disconnected";
        reconnectTimer = setTimeout(connect, 5000);
    };

    ws.onerror = () => {
        ws.close();
    };
}

onMounted(connect);
onUnmounted(() => {
    clearTimeout(reconnectTimer);
    ws?.close();
});
</script>

<style>
*,
*::before,
*::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: "Inter", sans-serif;
    background: #0d0d14;
    color: #e2e8f0;
    min-height: 100vh;
}
</style>

<style scoped>
.app {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1.5rem 2rem;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 1.25rem;
    border-bottom: 1px solid #1e1e2e;
    margin-bottom: 1.5rem;
}

.header-left {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

h1 {
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #a78bfa;
}

.subtitle {
    font-size: 0.8rem;
    color: #64748b;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.updated {
    font-size: 0.75rem;
    color: #475569;
}

.status {
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.status.connected {
    background: #14532d;
    color: #4ade80;
}

.status.connecting {
    background: #1c1917;
    color: #a8a29e;
}

.status.disconnected {
    background: #450a0a;
    color: #f87171;
}

.status.offline {
    background: #1c1917;
    color: #78716c;
}

/* Waiting state */
.waiting {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1.2rem;
    padding: 6rem 0;
    color: #475569;
}

.spinner {
    width: 36px;
    height: 36px;
    border: 3px solid #1e1e2e;
    border-top-color: #a78bfa;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

/* Table */
.table-wrap {
    overflow-x: auto;
    border-radius: 0.75rem;
    border: 1px solid #1e1e2e;
}

table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}

thead tr {
    background: #13131f;
}

th {
    padding: 0.75rem 1rem;
    text-align: left;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #475569;
    white-space: nowrap;
}

th:nth-child(1) {
    text-align: center;
}

th:nth-child(3),
th:nth-child(4),
th:nth-child(5),
th:nth-child(6),
th:nth-child(7) {
    text-align: right;
}

th.sortable {
    cursor: pointer;
    user-select: none;
    transition: color 0.15s;
}

th.sortable:hover {
    color: #94a3b8;
}

th.sortable.active {
    color: #a78bfa;
}

.sort-arrow {
    display: inline-block;
    width: 0.8em;
    font-style: normal;
    color: #2e3a4e;
}

th.sortable.active .sort-arrow {
    color: #a78bfa;
}

tbody tr {
    border-top: 1px solid #1a1a2e;
    transition: background 0.15s;
}

tbody tr:hover {
    background: #13131f;
}

tbody tr.top3 {
    background: #0f0f1f;
}

td {
    padding: 0.65rem 1rem;
    vertical-align: top;
}

.rank {
    width: 3rem;
    text-align: center;
}

.badge {
    display: inline-block;
    width: 1.6rem;
    height: 1.6rem;
    line-height: 1.6rem;
    border-radius: 50%;
    text-align: center;
    font-size: 0.75rem;
    font-weight: 700;
    background: #1e1e2e;
    color: #94a3b8;
}

.badge.rank-1 {
    background: #713f12;
    color: #fde68a;
}

.badge.rank-2 {
    background: #1c2637;
    color: #93c5fd;
}

.badge.rank-3 {
    background: #1c1917;
    color: #d6a87a;
}

.name {
    font-weight: 500;
    color: #f1f5f9;
    white-space: nowrap;
}

.number {
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}

.cost {
    color: #f87171;
}

.sell {
    color: #94a3b8;
}

.profit {
    color: #4ade80;
    font-weight: 600;
}

.pph {
    color: #a78bfa;
    font-weight: 600;
}

.recipe {
    color: #64748b;
    font-size: 0.78rem;
    line-height: 1.8;
}

.ingredient {
    display: block;
    white-space: nowrap;
}

.load-more {
    display: flex;
    justify-content: center;
    padding: 1rem;
    border-top: 1px solid #1e1e2e;
}

.load-more button {
    background: #13131f;
    color: #a78bfa;
    border: 1px solid #2e2e4e;
    border-radius: 0.5rem;
    padding: 0.5rem 1.25rem;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition:
        background 0.15s,
        border-color 0.15s;
}

.load-more button:hover {
    background: #1a1a2e;
    border-color: #a78bfa;
}

/* Tabs */
.tabs {
    display: flex;
    gap: 0.25rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #1e1e2e;
    padding-bottom: 0;
}

.tabs button {
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: #475569;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.6rem 1rem;
    cursor: pointer;
    margin-bottom: -1px;
    transition:
        color 0.15s,
        border-color 0.15s;
}

.tabs button:hover {
    color: #94a3b8;
}

.tabs button.active {
    color: #a78bfa;
    border-bottom-color: #a78bfa;
}

.content-page {
    line-height: 1.8;
    color: #cbd5e1;
}

.content-page h2 {
    font-size: 1.3rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 1.25rem;
}

.content-page h3 {
    font-size: 0.95rem;
    font-weight: 700;
    color: #a78bfa;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 1.75rem;
    margin-bottom: 0.5rem;
}

.content-page p {
    color: #94a3b8;
    margin-bottom: 0.75rem;
}

.content-page ul {
    list-style: none;
    padding: 0;
    margin-bottom: 0.75rem;
}

.content-page ul li {
    color: #94a3b8;
    padding: 0.2rem 0 0.2rem 1.25rem;
    position: relative;
}

.content-page ul li::before {
    content: "–";
    position: absolute;
    left: 0;
    color: #475569;
}

.content-page strong {
    color: #e2e8f0;
    font-weight: 600;
}

footer {
    display: flex;
    justify-content: center;
    padding: 2rem 0 1.5rem;
    margin-top: 2rem;
    border-top: 1px solid #1e1e2e;
}

.footer-link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: #475569;
    font-size: 0.78rem;
    text-decoration: none;
    transition: color 0.15s;
}

.footer-link:hover {
    color: #a78bfa;
}

.github-icon {
    width: 1.1rem;
    height: 1.1rem;
    flex-shrink: 0;
}

.content-page a {
    color: #a78bfa;
    text-decoration: underline;
    text-decoration-color: #4c3882;
    text-underline-offset: 2px;
    transition: color 0.15s, text-decoration-color 0.15s;
}

.content-page a:hover {
    color: #c4b5fd;
    text-decoration-color: #a78bfa;
}

.content-page em {
    color: #a78bfa;
    font-style: normal;
}

.content-page code {
    background: #1e1e2e;
    color: #a78bfa;
    padding: 0.1rem 0.4rem;
    border-radius: 0.25rem;
    font-size: 0.82rem;
}

/* Filter bar */
/* Tracker two-column layout */
.tracker-layout {
    display: flex;
    align-items: flex-start;
    gap: 1.25rem;
}

.filter-panel {
    flex: 0 0 13rem;
    background: #13131f;
    border: 1px solid #1e1e2e;
    border-radius: 0.75rem;
    padding: 1rem 1rem 0.75rem;
    position: sticky;
    top: 1rem;
}

.tracker-content {
    flex: 1;
    min-width: 0;
}

.filter-grid {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    margin-bottom: 0.75rem;
}

.filter-field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-size: 0.8rem;
}

.filter-controls {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.filter-label {
    color: #94a3b8;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.filter-field select {
    background: #0d0d14;
    border: 1px solid #2e2e4e;
    border-radius: 0.35rem;
    color: #e2e8f0;
    padding: 0.25rem 0.4rem;
    font-size: 0.8rem;
    cursor: pointer;
}

.filter-field select:focus {
    outline: none;
    border-color: #a78bfa;
}

.cost-input {
    width: 100%;
    max-width: 7rem;
    background: #0d0d14;
    border: 1px solid #2e2e4e;
    border-radius: 0.35rem;
    color: #e2e8f0;
    padding: 0.25rem 0.4rem;
    font-size: 0.8rem;
    text-align: center;
}

.cost-input:focus {
    outline: none;
    border-color: #a78bfa;
}

.cost-input:disabled {
    opacity: 0.2;
    cursor: not-allowed;
}

.no-budget-label {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    color: #64748b;
    font-size: 0.78rem;
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}

.no-budget-label input[type="checkbox"] {
    accent-color: #a78bfa;
    cursor: pointer;
    width: 0.85rem;
    height: 0.85rem;
}

.filter-max {
    color: #475569;
    font-size: 0.75rem;
    white-space: nowrap;
}

.filter-reset {
    background: none;
    border: 1px solid #2e2e4e;
    border-radius: 0.4rem;
    color: #64748b;
    font-size: 0.75rem;
    padding: 0.25rem 0.75rem;
    cursor: pointer;
    transition:
        color 0.15s,
        border-color 0.15s;
}

.filter-reset:hover {
    color: #f87171;
    border-color: #f87171;
}
</style>
