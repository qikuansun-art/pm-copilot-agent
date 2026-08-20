import { useEffect, useId, useMemo, useRef, useState } from "react";
import mermaid from "mermaid";

import { productFlowToMermaid } from "./flowMermaid";

mermaid.initialize({ startOnLoad: false, securityLevel: "strict", theme: "neutral" });

function BusinessFlowCard({ flow }) {
  const generatedId = useId();
  const containerRef = useRef(null);
  const [renderError, setRenderError] = useState(false);
  const definition = useMemo(() => productFlowToMermaid(flow), [flow]);

  useEffect(() => {
    let active = true;
    const renderId = `product-flow-${generatedId.replace(/[^A-Za-z0-9_-]/g, "")}`;
    setRenderError(false);
    if (containerRef.current) containerRef.current.replaceChildren();
    void mermaid.render(renderId, definition)
      .then(({ svg, bindFunctions }) => {
        if (!active || !containerRef.current) return;
        containerRef.current.innerHTML = svg;
        bindFunctions?.(containerRef.current);
      })
      .catch(() => {
        if (active) setRenderError(true);
      });
    return () => { active = false; };
  }, [definition, generatedId]);

  return (
    <section className="business-flow-section">
      <h3>业务流程 <span>Business Flow</span></h3>
      <article className="business-flow-card">
        <strong>{flow.title}</strong>
        <div className="business-flow-canvas">
          {renderError
            ? <p className="business-flow-error">流程图暂时无法显示</p>
            : <div className="business-flow-svg" ref={containerRef} />}
        </div>
        {flow.description && <p className="business-flow-description">{flow.description}</p>}
      </article>
    </section>
  );
}

export default BusinessFlowCard;
