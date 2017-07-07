from flask import Blueprint

from flask_security import login_required

from app.controllers import TemplateView

trackers = Blueprint('trackers', __name__)


class TrackersView(TemplateView):
    blueprint = trackers
    route = '/trackers'
    route_name = 'trackers'
    template_name = 'trackers/index.html'
    decorators = [login_required]

    def get_context_data(self, *args, **kwargs):
        return {
            'content': 'This is the profile page'
        }