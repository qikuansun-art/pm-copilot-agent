const labelReplacements = new Map([
  ['"', "'"], ["\n", " "], ["\r", " "], ["[", "［"], ["]", "］"],
  ["{", "｛"], ["}", "｝"], ["(", "（"], [")", "）"], ["|", "｜"],
  ["<", "＜"], [">", "＞"], ["&", "＆"], ["#", "＃"],
]);

function safeLabel(value = "") {
  return String(value)
    .replace(/["\n\r[\]{}()|<>&#]/g, (character) => labelReplacements.get(character) || character)
    .replace(/\s+/g, " ")
    .trim();
}

function nodeAliases(flow) {
  const aliases = new Map();
  const used = new Set();
  (flow.nodes || []).forEach((node, index) => {
    let base = String(node.id || "").replace(/[^A-Za-z0-9_]/g, "_");
    if (!base || /^\d/.test(base)) base = `n_${base || index + 1}`;
    let alias = base;
    let suffix = 2;
    while (used.has(alias)) {
      alias = `${base}_${suffix}`;
      suffix += 1;
    }
    aliases.set(node.id, alias);
    used.add(alias);
  });
  return aliases;
}

export function productFlowToMermaid(flow) {
  const aliases = nodeAliases(flow);
  const lines = ["flowchart TD"];
  (flow.nodes || []).forEach((node) => {
    const id = aliases.get(node.id);
    const label = safeLabel(node.label);
    if (node.node_type === "start" || node.node_type === "end") lines.push(`${id}([${label}])`);
    else if (node.node_type === "decision") lines.push(`${id}{${label}}`);
    else lines.push(`${id}[${label}]`);
  });
  (flow.edges || []).forEach((edge) => {
    const source = aliases.get(edge.source);
    const target = aliases.get(edge.target);
    const label = safeLabel(edge.label);
    lines.push(label ? `${source} -->|${label}| ${target}` : `${source} --> ${target}`);
  });
  return lines.join("\n");
}
