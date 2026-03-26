import { createStore } from "/js/AlpineStore.js";
import * as api from "/js/api.js";
import { closeModal, openModal } from "/js/modals.js";
import { store as chatTopStore } from "/components/chat/top-section/chat-top-store.js";
import {
  toastFrontendError,
  toastFrontendSuccess,
  toastFrontendWarning,
} from "/components/notifications/notification-store.js";

const modalPath = "modals/service-profile/service-profile.html";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

const model = {
  initialized: false,
  loaded: false,
  supported: false,
  restartStrategy: "managed_restart",
  currentProfile: "full",
  selectedProfile: "full",
  profiles: [],
  services: [],
  applying: false,
  error: "",

  get currentProfileLabel() {
    return this.profileLabel(this.currentProfile);
  },

  profileLabel(profileId) {
    return (
      this.profiles.find((profile) => profile.id === profileId)?.label ||
      profileId ||
      "Unknown"
    );
  },

  init() {
    if (this.initialized) return;
    this.initialized = true;
    this.refresh().catch((error) => {
      console.warn("Failed to initialize service profile store:", error);
    });
  },

  async refresh() {
    const snapshot = await api.callJsonApi("/service_profile_get", {});
    this.updateFromSnapshot(snapshot);
    return snapshot;
  },

  updateFromSnapshot(snapshot) {
    if (!snapshot) return;
    this.loaded = true;
    this.supported = !!snapshot.supported;
    this.restartStrategy = snapshot.restart_strategy || "managed_restart";
    this.currentProfile = snapshot.current_profile || this.currentProfile;
    this.profiles = Array.isArray(snapshot.profiles) ? snapshot.profiles : [];
    this.services = Array.isArray(snapshot.services) ? snapshot.services : [];
    if (!this.applying || !this.selectedProfile) {
      this.selectedProfile = this.currentProfile;
    }
  },

  updateFromStatus(snapshot) {
    if (snapshot) this.updateFromSnapshot(snapshot);
  },

  async closeModal() {
    return closeModal(modalPath);
  },

  async openModal() {
    if (!this.initialized) {
      this.init();
    }
    if (!this.supported) return;
    this.error = "";
    this.applying = false;
    await this.refresh().catch(() => null);
    return openModal(modalPath);
  },

  selectProfile(profileId) {
    if (this.applying) return;
    this.selectedProfile = profileId;
    this.error = "";
  },

  profileTransition(profileId) {
    const current = new Set(
      this.profiles.find((profile) => profile.id === this.currentProfile)?.services?.map((service) => service.id) || []
    );
    const target = new Set(
      this.profiles.find((profile) => profile.id === profileId)?.services?.map((service) => service.id) || []
    );
    return {
      enable: [...target].filter((service) => !current.has(service)),
      disable: [...current].filter((service) => !target.has(service)),
    };
  },

  serviceLabel(serviceId) {
    return (
      this.services.find((service) => service.id === serviceId)?.label ||
      this.profiles
        .flatMap((profile) => profile.services || [])
        .find((service) => service.id === serviceId)?.label ||
      serviceId
    );
  },

  async applySelectedProfile() {
    if (!this.supported || !this.selectedProfile || this.selectedProfile === this.currentProfile) {
      await this.closeModal();
      return;
    }

    this.applying = true;
    this.error = "";
    chatTopStore.setConnectionState("warming", "Switching service profile...");

    try {
      const response = await api.callJsonApi("/service_profile_set", {
        profile: this.selectedProfile,
      });
      this.currentProfile = response.selected_profile || this.selectedProfile;
      await this.waitForReconnect(this.currentProfile);
      chatTopStore.setConnectionState("ready", "Backend connected");
      await this.closeModal();
      toastFrontendSuccess(
        `Profile switched to ${this.profileLabel(this.currentProfile)}.`,
        "Service profile",
        4,
        "service-profile",
      );
    } catch (error) {
      this.error = error?.message || String(error);
      chatTopStore.setConnectionState("warming", "Profile switch needs attention.");
      toastFrontendError(
        `Profile switch failed: ${this.error}`,
        "Service profile",
        6,
        "service-profile",
      );
    } finally {
      this.applying = false;
    }
  },

  async waitForReconnect(expectedProfile) {
    const deadline = Date.now() + 90000;
    while (Date.now() < deadline) {
      try {
        const snapshot = await this.refresh();
        if (snapshot.current_profile === expectedProfile) {
          return snapshot;
        }
      } catch (_error) {
        // Backend is expected to be briefly unavailable during restart.
      }
      await sleep(2000);
    }
    toastFrontendWarning(
      "The runtime did not reconnect before timeout. Refresh if needed.",
      "Service profile",
      6,
      "service-profile-timeout",
    );
    throw new Error("Timed out waiting for the runtime to reconnect.");
  },
};

export const store = createStore("serviceProfile", model);
