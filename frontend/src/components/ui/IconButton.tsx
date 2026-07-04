import { ButtonHTMLAttributes, forwardRef } from "react";

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Tooltip/accessible name — mandatory: an icon alone is not a label. */
  title: string;
  variant?: "secondary" | "ghost";
}

/** Square icon-only button. `title` doubles as the aria-label. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { title, variant = "ghost", className, type, ...rest },
  ref,
) {
  const classes = ["lfui-btn", "lfui-iconbtn"];
  if (variant === "ghost") classes.push("lfui-btn--ghost");
  if (className) classes.push(className);
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={classes.join(" ")}
      title={title}
      aria-label={title}
      {...rest}
    />
  );
});
