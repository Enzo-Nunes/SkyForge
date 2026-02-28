<template>
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
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	lastUpdated: String,
	status: String,
});

const statusLabel = computed(
	() =>
		({
			connecting: "Connecting…",
			connected: "Live",
			disconnected: "Disconnected",
			offline: "Offline",
		})[props.status],
);
</script>

<style scoped>
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
</style>
