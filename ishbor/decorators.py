from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def candidate_only(view_func):
    """Faqat 'candidate' rolidagi foydalanuvchilar uchun ruxsat beradi."""
    @wraps(view_func)
    def wrapper_func(request, *args, **kwargs):
        # 1. Login qilganini tekshirish
        if not request.user.is_authenticated:
            return redirect('login')
        
        # 2. Roli 'candidate' ekanligini tekshirish
        if request.user.role == 'candidate':
            return view_func(request, *args, **kwargs)
        else:
            # Agar roli 'employer' bo'lsa, uni o'zining uy sahifasiga haydaymiz
            messages.error(request, "Siz ushbu sahifaga kirish huquqiga ega emassiz!")
            return redirect('employer_home') 
            
    return wrapper_func


def employer_only(view_func):
    """Faqat 'employer' rolidagi foydalanuvchilar uchun ruxsat beradi."""
    @wraps(view_func)
    def wrapper_func(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.role == 'employer':
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Siz ushbu sahifaga kirish huquqiga ega emassiz!")
            return redirect('candidate_home')
            
    return wrapper_func