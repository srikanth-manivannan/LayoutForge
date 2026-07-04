/** components/ui — the design-system primitive library
 * (docs/design/09_DESIGN_SYSTEM.md §6, reference styling in
 * docs/design/hifi/lf-mockup.css, classes in styles/ui.css).
 *
 * Rules:
 * - Primitives style through tokens only and never know about the domain.
 * - Feature panels compose primitives; new UI starts here, not with ad-hoc
 *   markup.
 * - Status is ALWAYS rendered via <Badge> so the taxonomy stays uniform.
 *
 * Tree and VirtualTable are deliberately not here yet — they land with
 * their first real consumers (2B thumbnails/search, 2C validation table)
 * so their APIs are shaped by real needs rather than guessed. */

export { Badge } from "./Badge";
export type { BadgeProps, BadgeStatus } from "./Badge";
export { Button } from "./Button";
export type { ButtonProps, ButtonSize, ButtonVariant } from "./Button";
export { EmptyState } from "./EmptyState";
export type { EmptyStateProps } from "./EmptyState";
export { IconButton } from "./IconButton";
export type { IconButtonProps } from "./IconButton";
export { Progress } from "./Progress";
export type { ProgressProps } from "./Progress";
export { Skeleton } from "./Skeleton";
export type { SkeletonProps } from "./Skeleton";
export { Slider } from "./Slider";
export type { SliderProps } from "./Slider";
export { Tabs } from "./Tabs";
export type { TabItem, TabsProps } from "./Tabs";
export { Toolbar, ToolbarSeparator, ToolbarSpacer } from "./Toolbar";
export type { ToolbarProps } from "./Toolbar";
