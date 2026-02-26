interface ApiVideoAssets {
  iframe?: string;
  player?: string;
  hls?: string;
  thumbnail?: string;
  mp4?: string;
}

interface ApiVideoVideo {
  videoId: string;
  title?: string;
  description?: string;
  publishedAt?: string;
  updatedAt?: string;
  tags?: string[];
  assets?: ApiVideoAssets;
}

interface ApiVideoListResponse {
  data: ApiVideoVideo[];
  pagination: {
    currentPage: number;
    pageSize: number;
    pagesTotal: number;
    itemsTotal: number;
  };
}

export async function listApiVideoVideos({
  pageSize,
  maxPages,
}: {
  pageSize: number;
  maxPages: number;
}): Promise<ApiVideoVideo[]> {
  const apiKey = process.env.APIVIDEO_API_KEY;
  if (!apiKey) {
    return [];
  }

  const baseUrl = process.env.APIVIDEO_BASE_URL?.replace(/\/$/, '') || 'https://ws.api.video';
  const results: ApiVideoVideo[] = [];

  for (let page = 1; page <= maxPages; page++) {
    const url = `${baseUrl}/videos?currentPage=${page}&pageSize=${pageSize}`;
    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        Accept: 'application/json',
      },
      next: { revalidate: 60 },
    });

    if (!res.ok) {
      break;
    }

    const body: ApiVideoListResponse = await res.json();
    results.push(...body.data);

    if (page >= body.pagination.pagesTotal) {
      break;
    }
  }

  return results;
}
