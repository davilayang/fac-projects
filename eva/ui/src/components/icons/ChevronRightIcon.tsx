import { iconSizes } from "./iconSizes";
import type { IconProps } from "./icon.types";

export function ChevronRightIcon({ className, size = "small" }: IconProps) {
  const px = iconSizes[size];
  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
      className={className}
    >
      <path
        d="M6 3l5 5-5 5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
