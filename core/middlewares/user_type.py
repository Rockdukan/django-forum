from django.shortcuts import redirect


class UserTypeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем доступ к админке только для сотрудников

        if request.path.startswith("/admin/") and request.user.is_authenticated:
            if hasattr(request.user, "profile") and request.user.profile.user_type != "employee":
                return redirect("client_dashboard")

        response = self.get_response(request)
        return response
