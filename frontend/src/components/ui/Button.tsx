import { ButtonHTMLAttributes, forwardRef } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

/** Design-system button (09_DESIGN_SYSTEM.md §6). `secondary` is the
 * default bordered style. Buttons that trigger app behavior should dispatch
 * a command in their onClick (via useCommand), never call services directly. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", className, type, ...rest },
  ref,
) {
  const classes = ["lfui-btn"];
  if (variant !== "secondary") classes.push(`lfui-btn--${variant}`);
  if (size === "sm") classes.push("lfui-btn--sm");
  if (className) classes.push(className);
  return <button ref={ref} type={type ?? "button"} className={classes.join(" ")} {...rest} />;
});
