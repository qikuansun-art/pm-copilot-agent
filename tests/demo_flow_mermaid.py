"""Regression coverage for deterministic ProductFlow Mermaid output."""

from models.flow import FlowEdge, FlowNode, ProductFlow
from utils.flow_mermaid import product_flow_to_mermaid


def main() -> None:
    """Verify shapes, branches, edges, determinism, and label safety."""
    flow = ProductFlow(
        title="维修流程",
        nodes=[
            FlowNode(id="n1", label="发现\n故障", node_type="start"),
            FlowNode(id="n2", label='创建[维修]"工单"'),
            FlowNode(id="n3", label="维修处理"),
            FlowNode(id="n4", label="维修是否完成?", node_type="decision"),
            FlowNode(id="n5", label="操作员确认"),
            FlowNode(id="n6", label="完成", node_type="end"),
        ],
        edges=[
            FlowEdge(source="n1", target="n2"),
            FlowEdge(source="n2", target="n3"),
            FlowEdge(source="n3", target="n4"),
            FlowEdge(source="n4", target="n5", label="是"),
            FlowEdge(source="n4", target="n3", label="否|重试"),
            FlowEdge(source="n5", target="n6"),
        ],
    )
    mermaid = product_flow_to_mermaid(flow)
    assert mermaid == product_flow_to_mermaid(flow)
    assert mermaid.startswith("flowchart TD\n")
    assert "n1([发现 故障])" in mermaid
    assert "n2[创建［维修］'工单']" in mermaid
    assert "n4{维修是否完成?}" in mermaid
    assert "n6([完成])" in mermaid
    assert "n4 -->|是| n5" in mermaid
    assert "n4 -->|否｜重试| n3" in mermaid
    for node in flow.nodes:
        assert node.id in mermaid
    assert mermaid.count("-->") == len(flow.edges)
    print(mermaid)


if __name__ == "__main__":
    main()
