import { useSettings, useSystem } from "../../api/settings";
import { plural } from "../../lib/format";
import { formatBytes } from "../../lib/settingsfmt";
import { Spinner } from "../Spinner";
import { CardHead } from "./CardHead";
import { JobsControl } from "./JobsControl";
import { Meter } from "./Meter";

/** Service settings: how many jobs run at once and what the container can give them. */
export function ServiceCard() {
  const system = useSystem().data;
  const settings = useSettings().data;
  const used =
    system?.memory.total != null && system.memory.available != null
      ? system.memory.total - system.memory.available
      : null;
  return (
    <section className="about-card settings-card" aria-labelledby="settings-service">
      <CardHead icon="queue" title="Service" id="settings-service" />
      {settings ? <JobsControl settings={settings} /> : <Spinner label="Reading settings" />}
      {system ? (
        <div className="settings-resources">
          <dl className="settings-facts">
            <div>
              <dt>Processor</dt>
              <dd>{plural(system.cores, "core")}</dd>
            </div>
            <div>
              <dt>Memory</dt>
              <dd>
                {formatBytes(system.memory.available)} free of {formatBytes(system.memory.total)}
                <span className="settings-chip">
                  {system.memory.source === "cgroup" ? "Container limit" : "Host"}
                </span>
              </dd>
            </div>
          </dl>
          <Meter
            label="Jobs running"
            value={system.workers.running}
            max={system.workers.configured}
            text={`${system.workers.running} of ${system.workers.configured}`}
          />
          <Meter
            label="Memory in use"
            value={used}
            max={system.memory.total}
            text={formatBytes(used)}
          />
          <Meter
            label="Cores reserved for jobs"
            value={system.workers.configured}
            max={system.cores}
            text={`${system.workers.configured} of ${system.cores}`}
          />
          <p className="settings-hint">
            The recommended maximum is the smaller of one less than the cores and the free memory
            divided by {system.fix_job_peak_mb} MB, the most one fix job needs.
          </p>
        </div>
      ) : (
        <Spinner label="Reading resources" />
      )}
    </section>
  );
}
