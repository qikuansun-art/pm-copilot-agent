"""Structured business-flow models for product plans."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FlowNode(BaseModel):
    """One node in a product business flow."""

    id: str
    label: str
    node_type: Literal["start", "step", "decision", "end"] = "step"


class FlowEdge(BaseModel):
    """One directed connection between two flow nodes."""

    source: str
    target: str
    label: str = ""


class ProductFlow(BaseModel):
    """A structured primary business flow for a product plan."""

    title: str
    description: str = ""
    nodes: list[FlowNode] = Field(default_factory=list)
    edges: list[FlowEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_graph(self) -> "ProductFlow":
        """Ensure node IDs are usable and every edge references the graph."""
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Flow node IDs must be unique")
        if sum(node.node_type == "start" for node in self.nodes) > 1:
            raise ValueError("A flow can contain at most one start node")
        if sum(node.node_type == "end" for node in self.nodes) > 1:
            raise ValueError("A flow can contain at most one end node")
        known_node_ids = set(node_ids)
        if any(
            edge.source not in known_node_ids or edge.target not in known_node_ids
            for edge in self.edges
        ):
            raise ValueError("Flow edges must reference existing node IDs")
        return self
