"""Technology Department supervisor — Alexandra."""

from supervisor_factory import build_supervisor_exports

from .config import default_config, metadata

_exports = build_supervisor_exports(metadata)

goal = _exports["goal"]
supervisor_goal = _exports["supervisor_goal"]
nodes = _exports["nodes"]
edges = _exports["edges"]
graph = _exports["graph"]
entry_node = _exports["entry_node"]
entry_points = _exports["entry_points"]
terminal_nodes = _exports["terminal_nodes"]
pause_nodes = _exports["pause_nodes"]
loop_config = _exports["loop_config"]
supervised_worker_path = _exports["supervised_worker_path"]
