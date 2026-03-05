import { ref, watch } from "vue";

function getInitialTheme() {
	// Check if user has a saved preference
	const saved = localStorage.getItem("theme");
	if (saved) {
		return saved;
	}

	// Check system preference
	if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
		return "dark";
	}

	// Default to dark if no system preference detected
	return "dark";
}

const theme = ref(getInitialTheme());

export function useTheme() {
	function setTheme(newTheme) {
		theme.value = newTheme;
		localStorage.setItem("theme", newTheme);
		document.documentElement.setAttribute("data-theme", newTheme);
	}

	function toggleTheme() {
		setTheme(theme.value === "dark" ? "light" : "dark");
	}

	// Set initial theme on app load
	if (!document.documentElement.hasAttribute("data-theme")) {
		document.documentElement.setAttribute("data-theme", theme.value);
	}

	// Listen for system theme changes
	if (window.matchMedia) {
		const darkModeQuery = window.matchMedia("(prefers-color-scheme: dark)");
		const handleSystemThemeChange = (e) => {
			// Only apply system change if user hasn't manually set a preference
			if (!localStorage.getItem("theme")) {
				setTheme(e.matches ? "dark" : "light");
			}
		};

		// Modern browsers support addEventListener on MediaQueryList
		if (darkModeQuery.addEventListener) {
			darkModeQuery.addEventListener("change", handleSystemThemeChange);
		}
	}

	return {
		theme,
		setTheme,
		toggleTheme,
	};
}
