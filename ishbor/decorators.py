from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings
from functools import wraps


def role_required(role_name):
    """Faqat belgilangan rolidagi foydalanuvchilar uchun ruxsat beradi."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role != role_name:
                messages.error(request, f"Ushbu sahifa faqat {role_name}lar uchun!")
                return redirect("home")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def rate_limit(max_attempts=None, lockout_time=None, key_prefix='rl'):
    """
    K7-FIX: Rate limiting dekorator — brute force hujumlaridan himoya.
    Cache yordamida IP manzil bo'yicha urinishlar sonini cheklaydi.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method != 'POST':
                return view_func(request, *args, **kwargs)

            _max = max_attempts or getattr(settings, 'LOGIN_MAX_ATTEMPTS', 5)
            _lockout = lockout_time or getattr(settings, 'LOGIN_LOCKOUT_TIME', 300)

            # IP manzilni aniqlash
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR', '0.0.0.0')

            cache_key = f'{key_prefix}:{ip}'
            attempts = cache.get(cache_key, 0)

            if attempts >= _max:
                remaining = cache.ttl(cache_key) if hasattr(cache, 'ttl') else _lockout
                minutes = remaining // 60 + 1
                messages.error(
                    request,
                    f"Juda ko'p urinish! Iltimos, {minutes} daqiqadan keyin qayta urinib ko'ring."
                )
                return redirect(request.path)

            response = view_func(request, *args, **kwargs)

            # Agar redirect bo'lmasa (ya'ni xato bo'lsa), urinishni oshiramiz
            if hasattr(response, 'status_code') and response.status_code == 200:
                cache.set(cache_key, attempts + 1, _lockout)

            return response
        return _wrapped_view
    return decorator