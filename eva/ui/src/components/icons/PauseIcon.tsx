import type { IconProps } from "./icon.types";
import { iconSizes } from "./iconSizes";

export function PauseIcon({ size = "small" }: IconProps) {
  const px = iconSizes[size];
  return (
    <svg width={px} height={px} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <rect x="6" y="4" width="4" height="16" />
      <rect x="14" y="4" width="4" height="16" />
    </svg>
  );
}
