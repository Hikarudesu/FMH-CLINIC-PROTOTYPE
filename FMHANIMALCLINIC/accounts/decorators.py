from functools import wraps

from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    Decorator that restricts a view to users whose role is in the given list.

    Usage:
        @login_required
        @role_required(User.Role.ADMIN, User.Role.BRANCH_ADMIN)
        def admin_only_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                if request.user.role in roles:
                    return view_func(request, *args, **kwargs)
                else:
                    # Redirect to their correct dashboard with a message
                    messages.warning(request, 'You do not have permission to access that page.')
                    if request.user.is_clinic_staff():
                        return redirect('admin_dashboard')
                    return redirect('user_dashboard')
                    
            # Fallback if not authenticated (though @login_required usually handles this)
            return redirect('login_page')
        return wrapper
    return decorator
