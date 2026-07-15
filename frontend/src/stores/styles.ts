import { defineStore } from "pinia";

import * as stylesApi from "@/api/styles";
import type {
  CreateStyleProfilePayload,
  StyleProfileDetail,
  StyleProfileSummary,
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
  },
});
