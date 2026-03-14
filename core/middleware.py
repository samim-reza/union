from django.utils.cache import add_never_cache_headers
from django.shortcuts import redirect
from django.urls import reverse

class NoCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            exempt_paths = {
                reverse('update-profile'),
                reverse('logout'),
                reverse('login'),
            }
            is_exempt = request.path in exempt_paths or request.path.startswith('/static/')
            profile = getattr(request.user, 'profile', None)
            is_profile_complete = bool(
                request.user.first_name
                and request.user.email
                and profile is not None
                and profile.date_of_birth is not None
            )
            if not is_exempt and not is_profile_complete:
                return redirect('update-profile')

        response = self.get_response(request)
        if request.user.is_authenticated:
            add_never_cache_headers(response)
        return response
