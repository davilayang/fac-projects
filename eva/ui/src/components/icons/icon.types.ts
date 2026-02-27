import { iconSizes } from "./iconSizes";

export type IconSize = keyof typeof iconSizes;

export interface IconProps {
  className?: string;
  size?: IconSize;
}
