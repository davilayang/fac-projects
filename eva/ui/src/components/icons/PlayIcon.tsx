import type { IconProps } from "./icon.types";
import { iconSizes } from "./iconSizes";

export function PlayIcon({ size = "small" }: IconProps) {
  const px = iconSizes[size];
  return (
    <svg width={px} height={px} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}
