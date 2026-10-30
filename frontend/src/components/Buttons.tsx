import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import { Icon, type IconName } from "./icons";
import { Tip } from "./Tip";

interface Common {
  icon: IconName;
  label: string;
  tip: string;
  /** Show the label next to the icon (hidden below 720px); otherwise screen readers only. */
  text?: boolean;
  variant?: "accent" | "primary" | "approve" | "reject" | "danger" | "warning" | "icon" | "plain";
  children?: ReactNode;
}

function content({ icon, label, text, children }: Common) {
  return (
    <>
      <Icon name={icon} />
      <span className={text ? "label-collapsible" : "sr"}>{label}</span>
      {children}
    </>
  );
}

function classes(c: Common, extra?: string): string {
  const v = c.variant ?? (c.text ? "plain" : "icon");
  return ["btn", v, extra ?? ""].filter(Boolean).join(" ");
}

type ButtonProps = Common & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children">;

export function ActionButton(props: ButtonProps) {
  const { icon, label, tip, text, variant, children, className, ...rest } = props;
  const common = { icon, label, tip, text, variant, children };
  return (
    <Tip text={tip}>
      <button type="button" {...rest} className={classes(common, className)}>
        {content(common)}
      </button>
    </Tip>
  );
}

type LinkButtonProps = Common & Omit<LinkProps, "children">;

export function ActionLink(props: LinkButtonProps) {
  const { icon, label, tip, text, variant, children, className, ...rest } = props;
  const common = { icon, label, tip, text, variant, children };
  return (
    <Tip text={tip}>
      <Link {...rest} className={classes(common, className)}>
        {content(common)}
      </Link>
    </Tip>
  );
}
