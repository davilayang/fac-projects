import { env, API_VIDEO_CONFIG } from "@eva-configs";

export interface ApiVideoAssetSet {
  thumbnail?: string;
  player?: string;
}

export interface ApiVideoMetadataItem {
  key: string;
  value: string;
}

export interface ApiVideoVideo {
  videoId: string;
  title?: string;
  description?: string;
  tags?: string[];
  metadata?: ApiVideoMetadataItem[];
  publishedAt?: string;
  updatedAt?: string;
  assets?: ApiVideoAssetSet;
}

export interface ApiVideoPagination {
  currentPage: number;
  pageSize: number;
  pagesTotal: number;
  itemsTotal: number;
  currentPageItems: number;
}

export interface ApiVideoListResponse {
  data: ApiVideoVideo[];
  pagination: ApiVideoPagination;
}

function buildListUrl(
  currentPage: number,
  pageSize: number,
  title?: string,
): URL {
  const url = new URL("/videos", API_VIDEO_CONFIG.BASE_URL);
  url.searchParams.set("currentPage", String(currentPage));
  url.searchParams.set("pageSize", String(pageSize));
  url.searchParams.set("sortBy", "publishedAt");
  url.searchParams.set("sortOrder", "desc");
  if (title) url.searchParams.set("title", title);
  return url;
}

export async function listPage(
  currentPage: number,
  pageSize: number = API_VIDEO_CONFIG.DEFAULT_PAGE_SIZE,
  title?: string,
): Promise<ApiVideoListResponse> {
  const response = await fetch(buildListUrl(currentPage, pageSize, title), {
    headers: {
      Authorization: `Bearer ${env.VITE_APIVIDEO_API_KEY}`,
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(
      `api.video list request failed: ${response.status} ${response.statusText}`,
    );
  }

  return (await response.json()) as ApiVideoListResponse;
}
