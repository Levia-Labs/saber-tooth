import { Icon, type IconName } from "../icons";

/** A settings card's icon tile and title, in the About card look. */
export function CardHead({ icon, title, id }: { icon: IconName; title: string; id: string }) {
  return (
    <div className="about-card-head">
      <span className="about-icon">
        <Icon name={icon} />
      </span>
      <h3 id={id}>{title}</h3>
    </div>
  );
}
