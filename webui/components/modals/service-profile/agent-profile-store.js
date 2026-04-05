import { createStore } from "/js/AlpineStore.js";
import * as api from "/js/api.js";
import {
  toastFrontendError,
  toastFrontendSuccess,
} from "/components/notifications/notification-store.js";

const model = {
  initialized: false,
  loaded: false,
  supported: false,
  currentProfile: "",
  selectedProfile: "",
  profiles: [],
  applying: false,
  error: "",

  get currentProfileLabel() {
    return this.profileLabel(this.currentProfile);
  },

  profileLabel(profileId) {
    return (
      this.profiles.find((p) => p.id === profileId)?.display_name ||
      profileId ||
      "Unknown"
    );
  },

  profileIcon(profileId) {
    return this.profiles.find((p) => p.id === profileId)?.icon || "🤖";
  },

  init() {
    if (this.initialized) return;
    this.initialized = true;
    this.refresh().catch((error) => {
      console.warn("Failed to initialize agent profile store:", error);
    });
  },

  async refresh() {
    try {
      const data = await api.callJsonApi("/agent_profile_get", {});
      this.updateFromSnapshot(data);
      return data;
    } catch (error) {
      console.warn("agent_profile_get failed:", error);
      return null;
    }
  },

  updateFromSnapshot(snapshot) {
    if (!snapshot) return;
    this.loaded = true;
    this.supported = !!snapshot.supported;
    this.currentProfile = snapshot.current_profile || this.currentProfile;
    this.profiles = Array.isArray(snapshot.profiles) ? snapshot.profiles : [];
    if (!this.applying || !this.selectedProfile) {
      this.selectedProfile = this.currentProfile;
    }
  },

  selectProfile(profileId) {
    if (this.applying) return;
    this.selectedProfile = profileId;
    this.error = "";
  },

  tierColor(tier) {
    const colors = {
      executive: "rgba(255, 184, 0, 0.22)",
      specialist: "rgba(0, 145, 255, 0.18)",
      orchestrator: "rgba(145, 70, 255, 0.18)",
      utility: "rgba(0, 195, 64, 0.15)",
      internal: "rgba(128, 128, 128, 0.15)",
    };
    return colors[tier] || colors.utility;
  },

  tierBorder(tier) {
    const colors = {
      executive: "rgba(255, 184, 0, 0.45)",
      specialist: "rgba(0, 145, 255, 0.38)",
      orchestrator: "rgba(145, 70, 255, 0.38)",
      utility: "rgba(0, 195, 64, 0.32)",
      internal: "rgba(128, 128, 128, 0.32)",
    };
    return colors[tier] || colors.utility;
  },

  async applySelectedProfile() {
    if (!this.supported || !this.selectedProfile || this.selectedProfile === this.currentProfile) {
      return;
    }

    this.applying = true;
    this.error = "";

    try {
      const response = await api.callJsonApi("/agent_profile_set", {
        profile: this.selectedProfile,
      });
      this.currentProfile = response.profile || this.selectedProfile;
      this.selectedProfile = this.currentProfile;
      toastFrontendSuccess(
        `Agent switched to ${this.profileLabel(this.currentProfile)}.`,
        "Agent profile",
        4,
        "agent-profile",
      );
    } catch (error) {
      this.error = error?.message || String(error);
      toastFrontendError(
        `Profile switch failed: ${this.error}`,
        "Agent profile",
        6,
        "agent-profile",
      );
    } finally {
      this.applying = false;
    }
  },
};

export const store = createStore("agentProfile", model);
