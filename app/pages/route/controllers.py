from flask import Blueprint

from flask_security import login_required

from app.controllers import TemplateView

route = Blueprint('route', __name__)


class RouteView(TemplateView):
    blueprint = route
    route = '/route'
    route_name = 'route'
    template_name = 'route/index.html'
    decorators = [login_required]

    def get_context_data(self, *args, **kwargs):
        return {
            'content': 'This is the profile page'
        }