"""GraphRAG ingest workflow."""

from engine.graph import EdgeCondition, EdgeSpec, GraphSpec, NodeSpec

ingest_node = NodeSpec(
    id="ingest",
    name="Ingest",
    description="Embed text and store in vector DB",
    node_type="event_loop",
    client_facing=True,
    input_keys=["text"],
    output_keys=["doc_id"],
    system_prompt="Call embed_and_insert with the user's text. Return the doc_id.",
    tools=["embed_and_insert"],
)
search_node = NodeSpec(
    id="search",
    name="Search",
    description="Retrieve relevant documents",
    node_type="event_loop",
    client_facing=False,
    input_keys=["query"],
    output_keys=["results"],
    system_prompt="Call vector_search with the query. Return the results.",
    tools=["vector_search"],
)
nodes = [ingest_node, search_node]
edges = [
    EdgeSpec(
        id="i2s",
        source="ingest",
        target="search",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]
graph = GraphSpec(
    id="graphrag-ingest",
    goal_id="graphrag",
    entry_node="ingest",
    nodes=nodes,
    edges=edges,
)
