from flask import Blueprint

from flask_security import login_required

from gpstracker_server.controllers import TemplateView

users = Blueprint('users', __name__)


class ProfileView(TemplateView):
    blueprint = users
    route = '/profile'
    route_name = 'profile'
    template_name = 'profiles/profile.html'
    decorators = [login_required]

    def get_context_data(self, *args, **kwargs):
        return {
            'content': 'This is the profile page'
        }
