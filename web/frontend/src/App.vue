<template>
	<div class="app" :data-theme="theme">
		<AppHeader :lastUpdated="lastUpdated" :status="status" :uptimeSeconds="uptimeSeconds" />

		<nav class="tabs">
			<button :class="{ active: tab === 'tracker' }" @click="tab = 'tracker'">Tracker</button>
			<button :class="{ active: tab === 'guide' }" @click="tab = 'guide'">Guide</button>
			<button :class="{ active: tab === 'how' }" @click="tab = 'how'">How does it work?</button>
		</nav>

		<TrackerTab
			v-if="tab === 'tracker'"
			:profits="profits"
			:uptimeSeconds="uptimeSeconds"
			@go-to-guide="tab = 'guide'"
		/>
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
import { useTheme } from "./composables/useTheme.js";

const profits = ref([]);
const status = ref("connecting");
const lastUpdated = ref(null);
const uptimeSeconds = ref(null);
const tab = ref("tracker");
const { theme } = useTheme();

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
	background: var(--bg-primary);
	color: var(--text-primary);
	min-height: 100vh;
}

/* Shared content page styles (used by GuideTab and HowTab) */
.content-page {
	line-height: 1.8;
	color: var(--text-secondary);
}

.content-page h2 {
	font-size: 1.3rem;
	font-weight: 700;
	color: var(--text-accent);
	margin-bottom: 1.25rem;
}

.content-page h3 {
	font-size: 0.95rem;
	font-weight: 700;
	color: var(--accent);
	text-transform: uppercase;
	letter-spacing: 0.05em;
	margin-top: 1.75rem;
	margin-bottom: 0.5rem;
}

.content-page p {
	color: var(--text-tertiary);
	margin-bottom: 0.75rem;
}

.content-page ul {
	list-style: none;
	padding: 0;
	margin-bottom: 0.75rem;
}

.content-page ul li {
	color: var(--text-tertiary);
	padding: 0.2rem 0 0.2rem 1.25rem;
	position: relative;
}

.content-page ul li::before {
	content: "–";
	position: absolute;
	left: 0;
	color: var(--text-muted);
}

.content-page strong {
	color: var(--text-primary);
	font-weight: 600;
}

.content-page a {
	color: var(--accent);
	text-decoration: underline;
	text-decoration-color: var(--accent-dark);
	text-underline-offset: 2px;
	transition:
		color 0.15s,
		text-decoration-color 0.15s;
}

.content-page a:hover {
	color: var(--accent-light);
	text-decoration-color: var(--accent);
}

.content-page em {
	color: var(--accent);
	font-style: normal;
}

.content-page code {
	background: var(--bg-secondary);
	color: var(--accent);
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
	transition: all 0.3s;
}

.tabs {
	display: flex;
	gap: 0.25rem;
	margin-bottom: 1.5rem;
	border-bottom: 1px solid var(--border);
	padding-bottom: 0;
	transition: border-color 0.3s;
}

.tabs button {
	background: none;
	border: none;
	border-bottom: 2px solid transparent;
	color: var(--text-muted);
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
	color: var(--text-tertiary);
}

.tabs button.active {
	color: var(--accent);
	border-bottom-color: var(--accent);
}
</style>
