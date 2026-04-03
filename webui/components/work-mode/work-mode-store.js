import { createStore } from "/js/AlpineStore.js";

// define the model object holding data and functions
const model = {
  current: "local",
  label: "Local",
  switching: false,

  labels: {
    local: "Local",
    selective: "Controlled",
    cloud: "Cloud",
  },

  colors: {
    local: "text-amber-600",
    selective: "text-blue-600",
    cloud: "text-emerald-600",
  },

  async init() {
    await this.fetchMode();
  },

  async fetchMode() {
    try {
      const res = await fetch("/api/work_mode");
      if (res.ok) {
        const data = await res.json();
        this.current = data.mode;
        this.label = this.labels[data.mode] || data.mode;
      }
    } catch (e) {
      console.warn("work-mode fetch failed", e);
    }
  },

  async requestSwitch(newMode) {
    this.switching = true;
    try {
      const res = await fetch("/api/work_mode_set", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: newMode }),
      });
      if (res.ok) {
        const data = await res.json();
        this.current = data.mode;
        this.label = this.labels[data.mode] || data.mode;
      }
    } catch (e) {
      console.error("mode switch failed", e);
    } finally {
      this.switching = false;
    }
  },

  get colorClass() {
    return this.colors[this.current] || "text-gray-500";
  },
};

// convert it to alpine store
const store = createStore("workMode", model);

// export for use in other files
export { store };
