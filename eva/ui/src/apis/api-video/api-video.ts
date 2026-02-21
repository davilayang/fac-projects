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

const APIVIDEO_API_KEY = import.meta.env.VITE_APIVIDEO_API_KEY as string | undefined;
export const PAGE_SIZE = 12;

function buildListUrl(currentPage: number, pageSize: number): URL {
  const url = new URL("/videos", "https://ws.api.video");
  url.searchParams.set("currentPage", String(currentPage));
  url.searchParams.set("pageSize", String(pageSize));
  url.searchParams.set("sortBy", "publishedAt");
  url.searchParams.set("sortOrder", "desc");
  return url;
}

export async function listPage(
  currentPage: number,
  pageSize: number = PAGE_SIZE,
): Promise<ApiVideoListResponse> {
  if (!APIVIDEO_API_KEY) {
    throw new Error("VITE_APIVIDEO_API_KEY is not configured");
  }

  const response = await fetch(buildListUrl(currentPage, pageSize), {
    headers: {
      Authorization: `Bearer ${APIVIDEO_API_KEY}`,
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
