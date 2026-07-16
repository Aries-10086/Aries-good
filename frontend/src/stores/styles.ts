import { defineStore } from "pinia";

import * as stylesApi from "@/api/styles";
import type {
  CreateStyleProfilePayload,
  StyleProfileDetail,
  StyleProfileSummary,
  UpdateStyleProfilePayload,
} from "@/types";

type StylesState = {
  profiles: StyleProfileSummary[];
  currentProfile: StyleProfileDetail | null;
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  creating: boolean;
};

export const useStylesStore = defineStore("styles", {
  state: (): StylesState => ({
    profiles: [],
    currentProfile: null,
    total: 0,
    page: 1,
    pageSize: 20,
    loading: false,
    creating: false,
  }),
  actions: {
    async fetchProfiles(page = this.page) {
      this.loading = true;
      try {
        const response = await stylesApi.listStyleProfiles(page, this.pageSize);
        this.profiles = response.results;
        this.total = response.count;
        this.page = page;
      } finally {
        this.loading = false;
      }
    },
    async fetchProfile(profileId: string) {
      this.loading = true;
      try {
        this.currentProfile = await stylesApi.getStyleProfile(profileId);
        return this.currentProfile;
      } finally {
        this.loading = false;
      }
    },
    async createProfile(payload: CreateStyleProfilePayload) {
      this.creating = true;
      try {
        const profile = await stylesApi.createStyleProfile(payload);
        this.currentProfile = profile;
        return profile;
      } finally {
        this.creating = false;
      }
    },
    async updateProfile(profileId: string, payload: UpdateStyleProfilePayload) {
      const profile = await stylesApi.updateStyleProfile(profileId, payload);
      this.currentProfile = profile;
      const index = this.profiles.findIndex((item) => item.profile_id === profileId);
      if (index >= 0) {
        this.profiles[index] = profile;
      }
      return profile;
    },
    async deleteProfile(profileId: string) {
      await stylesApi.deleteStyleProfile(profileId);
      this.profiles = this.profiles.filter((item) => item.profile_id !== profileId);
      this.total = Math.max(0, this.total - 1);
      if (this.currentProfile?.profile_id === profileId) {
        this.currentProfile = null;
      }
    },
  },
});
