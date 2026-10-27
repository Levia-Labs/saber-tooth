import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link, type LinkProps } from "react-router";
import { Icon, type IconName } from "./icons";
import { Tip } from "./Tip";

interface Common {
  icon: IconName;
  label: string;
  tip: string;
  /** Show the label next to the icon; otherwise it is read by screen readers only. */
  text?: boolean;
  variant?: "primary" | "approve" | "reject" | "icon" | "plain";
  /** Short visible label shown only in the mobile card layout. */
  short?: string;
  children?: ReactNode;
}

function content({ icon, label, text, short, children }: Common) {
  return (
    <>
      <Icon name={icon} />
      <span className={text ? "" : "sr"}>{label}</span>
      {short && !text && (
        <span className="short" aria-hidden="true">
          {short}
        </span>
      )}
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
  const { icon, label, tip, text, variant, short, children, className, ...rest } = props;
  const common = { icon, label, tip, text, variant, short, children };
  return (
    <Tip text={tip} info={text}>
      <button type="button" {...rest} className={classes(common, className)}>
        {content(common)}
      </button>
    </Tip>
  );
}

type LinkButtonProps = Common & Omit<LinkProps, "children">;

export function ActionLink(props: LinkButtonProps) {
  const { icon, label, tip, text, variant, short, children, className, ...rest } = props;
  const common = { icon, label, tip, text, variant, short, children };
  return (
    <Tip text={tip} info={text}>
      <Link {...rest} className={classes(common, className)}>
        {content(common)}
      </Link>
    </Tip>
  );
}
