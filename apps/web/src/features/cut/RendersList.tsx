import { renderFileUrl } from "../../api/client";
import type { Render } from "../../api/types";
import { formatDateTime, formatDuration } from "../../ui/format";
import { exportSummary } from "./exportSummary";

/** The cut's exports, as the Exportar menu of the prototype lists them, each with Baixar; the
 * API names the downloaded file. Nothing shows while there is none. */
export function RendersList({ renders }: { renders: Render[] }) {
  if (!renders.length) {
    return null;
  }
  return (
    <>
      <p className="msep" id="renders-heading">
        Exportações
      </p>
      <ul className="mlist" aria-labelledby="renders-heading">
        {renders.map((render) => {
          const when = formatDateTime(render.created_at);
          return (
            <li className="mi" key={render.id}>
              <b>{when}</b>
              <small>
                9:16 · {formatDuration(render.duration)} · {exportSummary(render.options)}
              </small>
              <a
                className="btn sm ghost"
                href={renderFileUrl(render.id)}
                download
                aria-label={`Baixar a exportação de ${when}`}
              >
                Baixar
              </a>
            </li>
          );
        })}
      </ul>
    </>
  );
}
