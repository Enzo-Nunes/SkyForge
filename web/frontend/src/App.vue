<template>
	<div class="app">
		<AppHeader :lastUpdated="lastUpdated" :status="status" :uptimeSeconds="uptimeSeconds" />

		<nav class="tabs">
			<button :class="{ active: tab === 'tracker' }" @click="tab = 'tracker'">Tracker</button>
			<button :class="{ active: tab === 'guide' }" @click="tab = 'guide'">Guide</button>
			<button :class="{ active: tab === 'how' }" @click="tab = 'how'">How does it work?</button>
		</nav>

		<TrackerTab v-if="tab === 'tracker'" :profits="profits" />
		<GuideTab v-else-if="tab === 'guide'" />
		<HowTab v-else-if="tab === 'how'" />
	</div>

	<AppFooter />
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import AppHeader from "./components/AppHeader.vue";
import AppFooter from "./components/AppFooter.vue";
import TrackerTab from "./components/TrackerTab.vue";
import GuideTab from "./components/GuideTab.vue";
import HowTab from "./components/HowTab.vue";

const profits = ref([]);
const status = ref("connecting");
const lastUpdated = ref(null);
const uptimeSeconds = ref(null);
const tab = ref("tracker");

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
			lastUpdated.value = new Date(data.calculated_at).toLocaleTimeString(undefined, { timeZoneName: "short" });
			uptimeSeconds.value = data.uptime_seconds;
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

/* Shared content page styles (used by GuideTab and HowTab) */
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
</style>

<style scoped>
.app {
	width: 90%;
	margin: 0 auto;
	padding: 1.5rem 0;
}

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
</style>
