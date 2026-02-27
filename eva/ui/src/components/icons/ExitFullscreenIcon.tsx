import type { IconProps } from "./icon.types";
import { iconSizes } from "./iconSizes";

export function ExitFullscreenIcon({ size = "small" }: IconProps) {
  const px = iconSizes[size];
  return (
    <svg width={px} height={px} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="4 14 10 14 10 20" />
      <polyline points="20 10 14 10 14 4" />
      <line x1="10" y1="14" x2="3" y2="21" />
      <line x1="21" y1="3" x2="14" y2="10" />
    </svg>
  );
}
