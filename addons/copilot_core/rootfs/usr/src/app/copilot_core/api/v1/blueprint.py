from flask import Blueprint

from copilot_core.api.v1.candidates import bp as candidates_bp
from copilot_core.api.v1.dev import bp as dev_bp
from copilot_core.api.v1.events import bp as events_bp
from copilot_core.api.v1.mood import bp as mood_bp
from copilot_core.api.v1.graph import bp as graph_bp
from copilot_core.api.v1.habitus import bp as habitus_bp
from copilot_core.api.v1.habitus_dashboard_cards import bp as dashboard_cards_bp
from copilot_core.api.v1.graph_ops import bp as graph_ops_bp
from copilot_core.knowledge_graph.api import bp as knowledge_graph_bp

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

# Compose sub-modules.
api_v1.register_blueprint(dev_bp)
api_v1.register_blueprint(events_bp)
api_v1.register_blueprint(candidates_bp)
api_v1.register_blueprint(mood_bp)
api_v1.register_blueprint(graph_bp)
api_v1.register_blueprint(habitus_bp)
api_v1.register_blueprint(dashboard_cards_bp)
api_v1.register_blueprint(graph_ops_bp)
api_v1.register_blueprint(knowledge_graph_bp)
