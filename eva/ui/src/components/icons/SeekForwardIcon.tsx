import type { IconProps } from "./icon.types";
import { iconSizes } from "./iconSizes";

export function SeekForwardIcon({ size = "medium" }: IconProps) {
  const px = iconSizes[size];
  return (
    <svg width={px} height={px} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M18 13c0 3.31-2.69 6-6 6s-6-2.69-6-6 2.69-6 6-6v4l5-5-5-5v4c-4.42 0-8 3.58-8 8s3.58 8 8 8 8-3.58 8-8h-2z" />
    </svg>
  );
}
