interface ApiVideoConfig {
  BASE_URL: string;
  DEFAULT_PAGE_SIZE: number;
}

export const API_VIDEO_CONFIG = {
  BASE_URL: "https://ws.api.video",
  DEFAULT_PAGE_SIZE: 12,
} satisfies ApiVideoConfig;
