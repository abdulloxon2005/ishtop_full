from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from functools import wraps
import json

from .forms import (
    RoleChooseForm, CandidateRegisterForm, 
    EmployerRegisterForm, VacancyForm, ApplicationForm, EmployerProfileForm,
    validate_resume_file
)
from .models import (
    CandidateProfile, EmployerProfile, Consent, 
    Vacancy, Application, Resume, Interview, User
)


def get_client_ip(request):
    """Foydalanuvchining IP manzilini aniqlash."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')

# ==========================================
# CUSTOM DECORATORS
# ==========================================
def role_required(role_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # login_required allaqachon tekshiradi, biz faqat rolni tekshiramiz
            if request.user.role != role_name:
                messages.error(request, f"Ushbu sahifa faqat {role_name}lar uchun!")
                return redirect("home")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

# ==========================================
# ASOSIY VA AVTORIZATSIYA
# ==========================================
def home_views(request):
    return render(request, "home.html")

def login_view(request):
    if request.user.is_authenticated:
        return redirect("employer_home" if request.user.role == "employer" else "candidate_home")
        
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, f"Xush kelibsiz, {user.username}!")
            return redirect("employer_home" if user.role == "employer" else "candidate_home")
        
        messages.error(request, "Login yoki parol xato!")
    return render(request, "login.html")

def logout_view(request):
    """Logout — faqat POST so'rov orqali."""
    if request.method == "POST":
        logout(request)
        return redirect("login")
    # GET so'rov kelsa ham chiqarish (orqaga muvofiqligi uchun)
    logout(request)
    return redirect("login")

# ==========================================
# RO'YXATDAN O'TISH
# ==========================================
@csrf_protect
def choose_role(request):
    form = RoleChooseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        role = form.cleaned_data["role"]
        request.session['chosen_role'] = role # Rolni sessiyada saqlash xavfsizroq
        return redirect("register_candidate" if role == "candidate" else "register_employer")
    return render(request, "choose_role.html", {"form": form})

@transaction.atomic
def register_candidate(request):
    form = CandidateRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        CandidateProfile.objects.create(
            user=user, 
            phone=user.phone # User modelidagi phone-ni profilga ham nusxalash
        )
        Consent.objects.create(user=user, consent_text="Ish izlovchi roziligi")
        
        login(request, user)
        res = redirect("candidate_home")
        res.set_cookie("gdpr_consent", "accepted", max_age=2592000, httponly=True, samesite='Lax')
        return res
    return render(request, "register_candidate.html", {"form": form})

@transaction.atomic
def register_employer(request):
    form = EmployerRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        EmployerProfile.objects.create(
            user=user, 
            company_name=form.cleaned_data["company_name"],
            stir=form.cleaned_data["stir"],
            company_address=form.cleaned_data["company_address"],
            company_phone=form.cleaned_data["company_phone"],
            responsible_full_name=form.cleaned_data["responsible_full_name"]
        )
        Consent.objects.create(user=user, consent_text="Ish beruvchi roziligi")
        
        login(request, user)
        res = redirect("employer_home")
        res.set_cookie("gdpr_consent", "accepted", max_age=2592000, httponly=True, samesite='Lax')
        return res
    return render(request, "register_employer.html", {"form": form})

# ==========================================
# ISH BERUVCHI PANELI
# ==========================================
@login_required
@role_required("employer")
def employer_home(request):
    return render(request, "employer/employer_home.html")

@login_required
@role_required("employer")
def vacancy_list(request):
    vacancies = request.user.vacancies.all()
    return render(request, "employer/vacancy_list.html", {"vacancies": vacancies})

@login_required
@role_required("employer")
def vacancy_create(request):
    form = VacancyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        vacancy = form.save(commit=False)
        vacancy.employer = request.user
        vacancy.save()
        messages.success(request, "Vakansiya muvaffaqiyatli yaratildi.")
        return redirect("vacancy_list")
    return render(request, "employer/vacancy_create.html", {"form": form})

@login_required
@role_required("employer")
def vacancy_update(request, id):
    vacancy = get_object_or_404(Vacancy, id=id, employer=request.user)
    form = VacancyForm(request.POST or None, instance=vacancy)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "O'zgarishlar saqlandi.")
        return redirect("vacancy_list")
    return render(request, "employer/vacancy_create.html", {"form": form, "edit_mode": True})

@login_required
@role_required("employer")
def vacancy_delete(request, id):
    vacancy = get_object_or_404(Vacancy, id=id, employer=request.user)
    if request.method == "POST":
        vacancy.delete()
        messages.warning(request, "Vakansiya o'chirildi.")
        return redirect("vacancy_list")
    return render(request, "employer/vacancy_confirm_delete.html", {"vacancy": vacancy})

@login_required
@role_required("employer")
def employer_applications_list(request):
    applications = Application.objects.filter(
        vacancy__employer=request.user
    ).select_related('vacancy', 'user', 'resume').order_by('-created_at')
    return render(request, 'employer/view_applications.html', {'applications': applications})

@login_required
@role_required("employer")
@require_POST
def update_application_status(request, app_id, new_status):
    """Ariza statusini yangilash — faqat POST orqali."""
    application = get_object_or_404(Application, id=app_id, vacancy__employer=request.user)
    valid_statuses = ['reviewed', 'accepted', 'rejected']
    if new_status in valid_statuses:
        application.status = new_status
        application.save()
        messages.success(request, f"Ariza holati yangilandi: {application.get_status_display()}")
    else:
        messages.error(request, "Noto'g'ri holat kiritildi.")
    return redirect('employer_applications_list')

@login_required
@role_required("employer")
def edit_employer_profile(request):
    profile, created = EmployerProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = EmployerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Kompaniya profili yangilandi.")
            return redirect('employer_home')
    else:
        form = EmployerProfileForm(instance=profile)
    return render(request, 'employer/edit_profile.html', {'form': form, 'profile': profile})

# Ish beruvchi suhbat belgilashi uchun
@login_required
@role_required("employer")
def schedule_interview(request, app_id):
    application = get_object_or_404(Application, id=app_id, vacancy__employer=request.user)
    
    if request.method == 'POST':
        date_time = request.POST.get('date_time')
        location_link = request.POST.get('location_link')
        notes = request.POST.get('notes')
        
        # Suhbatni yaratamiz yoki yangilaymiz
        interview, created = Interview.objects.update_or_create(
            application=application,
            defaults={
                'date_time': date_time,
                'location_link': location_link,
                'notes': notes,
                'status': 'pending'
            }
        )
        
        # Ariza holatini avtomatik 'accepted' ga o'tkazish
        application.status = 'accepted'
        application.save()
        
        messages.success(request, "Suhbat muvaffaqiyatli belgilandi va nomzodga yuborildi!")
        return redirect('employer_applications_list')
    
    return render(request, 'employer/schedule_interview.html', {'application': application})

# Nomzod suhbatni qabul qilishi yoki rad etishi uchun
@login_required
@role_required("candidate")
@require_POST
def respond_to_interview(request, interview_id, decision):
    """Suhbat taklifiga javob berish — faqat POST orqali."""
    interview = get_object_or_404(Interview, id=interview_id, application__user=request.user)
    
    if decision == 'accept':
        interview.status = 'accepted'
        messages.success(request, "Suhbat muvaffaqiyatli qabul qilindi!")
    elif decision == 'reject':
        interview.status = 'rejected'
        messages.warning(request, "Suhbat rad etildi.")
    else:
        messages.error(request, "Noto'g'ri amal.")
        return redirect('candidate_home')
    
    interview.save()
    return redirect('candidate_home')


@login_required
@role_required("employer")
def edit_interview(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)

    if interview.application.vacancy.employer != request.user:
        messages.error(request, "Sizda bu amalni bajarishga ruxsat yo'q.")
        return redirect('employer_home')

    if request.method == "POST":
        new_date = request.POST.get('date_time')
        new_link = request.POST.get('location_link')
        new_notes = request.POST.get('notes')

        if new_date and new_link:
            interview.date_time = new_date
            interview.location_link = new_link
            interview.notes = new_notes
            interview.status = 'pending'
            interview.save()

            messages.success(request, "Suhbat ma'lumotlari yangilandi.")
            return redirect('employer_applications_list')

        messages.error(request, "Sana va havola kiritilishi shart.")

    return render(request, "employer/edit_interview.html", {
        "interview": interview
    })

@login_required
@role_required("employer")
@require_POST
def delete_interview(request, interview_id):
    """Suhbatni o'chirish — faqat POST orqali."""
    interview = get_object_or_404(Interview, id=interview_id)
    
    if interview.application.vacancy.employer == request.user:
        interview.delete()
        messages.success(request, "Suhbat taklifi bekor qilindi.")
    else:
        messages.error(request, "Ruxsat etilmadi.")
        
    return redirect('employer_applications_list')


# ==========================================
# ISH IZLOVCHI PANELI
# ==========================================
@login_required
@role_required("candidate")
def candidate_home(request):
    user_applications = Application.objects.filter(user=request.user).select_related(
        'vacancy', 
        'vacancy__employer__employer_profile',
    ).order_by('-created_at')
    
    # Suhbat takliflari bor-yo'qligini xavfsiz tekshirish
    has_interviews = False
    for app in user_applications:
        try:
            if app.interview:
                has_interviews = True
                break
        except Interview.DoesNotExist:
            pass
    
    resumes_count = Resume.objects.filter(user=request.user).count()
    
    context = {
        'user_applications': user_applications,
        'has_interviews': has_interviews,
        'total_applications': user_applications.count(),
        'resumes_count': resumes_count,
        'recent_applications': user_applications[:5],
    }
    return render(request, "candidate/candidate_home.html", context)



@login_required
@role_required("candidate")
def apply_for_job(request, vacancy_id):
    vacancy = get_object_or_404(Vacancy, id=vacancy_id)
    
    if Application.objects.filter(vacancy=vacancy, user=request.user).exists():
        messages.warning(request, "Siz bu vakansiyaga allaqachon ariza topshirgansiz.")
        return redirect('vacancy_detail', pk=vacancy.id)

    resumes = request.user.resumes.all()

    if request.method == 'POST':
        selected_resume_id = request.POST.get('resume_id')
        consent_given = request.POST.get('data_consent') in ['on', 'true', '1']

        if not consent_given:
            messages.error(request, "Rozilik berishingiz shart!")
        elif not selected_resume_id:
            messages.error(request, "Rezyumeni tanlang!")
        else:
            selected_resume = get_object_or_404(Resume, id=selected_resume_id, user=request.user)
            Application.objects.create(
                vacancy=vacancy,
                user=request.user,
                resume=selected_resume,
                status='pending'
            )
            messages.success(request, "Arizangiz yuborildi!")
            return redirect('vacancy_detail', pk=vacancy.id)

    return render(request, 'candidate/apply_job.html', {'vacancy': vacancy, 'resumes': resumes})

def job_list(request):
    query = request.GET.get('q')
    location = request.GET.get('location')
    jobs = Vacancy.objects.filter(is_active=True).order_by('-created_at')

    if query:
        jobs = jobs.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if location:
        jobs = jobs.filter(location__icontains=location)

    return render(request, 'candidate/job_list.html', {'jobs': jobs})

def vacancy_detail(request, pk):
    vacancy = get_object_or_404(Vacancy, id=pk)
    has_applied = False
    if request.user.is_authenticated:
        has_applied = Application.objects.filter(vacancy=vacancy, user=request.user).exists()
    
    return render(request, 'candidate/vacancy_detail.html', {'vacancy': vacancy, 'has_applied': has_applied})

@login_required
@role_required("candidate")
def candidate_profile_view(request):
    profile, created = CandidateProfile.objects.get_or_create(user=request.user)
    resumes = request.user.resumes.all()

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'personal_info':
            profile.phone = request.POST.get('phone')
            profile.bio = request.POST.get('bio')
            if request.FILES.get('image'):
                profile.image = request.FILES.get('image')
            profile.save()
            messages.success(request, "Profil yangilandi.")
        elif form_type == 'gdpr_settings':
            profile.gdpr_consent = 'gdpr_consent' in request.POST
            profile.save()
            messages.info(request, "Sozlamalar saqlandi.")
        return redirect('candidate_profile')

    return render(request, 'candidate/profile.html', {'profile': profile, 'resumes': resumes})

@login_required
@role_required("candidate")
def resume_create(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        file = request.FILES.get('file')
        if title and file:
            # Fayl turini tekshirish
            try:
                validate_resume_file(file)
                Resume.objects.create(user=request.user, title=title, file=file)
                messages.success(request, "Rezyume qo'shildi.")
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Ma'lumotlar to'liq emas.")
    return redirect('candidate_profile')

@login_required
@role_required("candidate")
def resume_delete(request, id):
    resume = get_object_or_404(Resume, id=id, user=request.user)
    if request.method == 'POST':
        resume.delete()
        messages.warning(request, "Rezyume o'chirildi.")
        return redirect('candidate_profile')
    return redirect('candidate_profile')


# ==========================================
# GDPR SAHIFALARI
# ==========================================
def privacy_policy_view(request):
    """Maxfiylik siyosati sahifasi."""
    return render(request, 'gdpr/privacy.html')

def terms_of_service_view(request):
    """Foydalanish shartlari sahifasi."""
    return render(request, 'gdpr/terms.html')

def gdpr_policy_view(request):
    """GDPR siyosati sahifasi."""
    return render(request, 'gdpr/gdpr_policy.html')


@login_required
def export_user_data(request):
    """Foydalanuvchi ma'lumotlarini JSON formatda eksport qilish (GDPR — Data Portability)."""
    user = request.user
    
    # Asosiy foydalanuvchi ma'lumotlari
    data = {
        'account': {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'role': user.role,
            'date_joined': user.date_joined.isoformat(),
        },
        'consents': [],
        'applications': [],
    }

    # Roziliklar tarixi
    for c in Consent.objects.filter(user=user):
        data['consents'].append({
            'type': c.consent_type,
            'text': c.consent_text,
            'is_active': c.is_active,
            'accepted_at': c.accepted_at.isoformat(),
        })

    # Rol bo'yicha qo'shimcha ma'lumotlar
    if user.role == 'candidate':
        try:
            profile = user.candidate_profile
            data['profile'] = {
                'phone': profile.phone,
                'bio': profile.bio,
                'skills': profile.skills,
                'gdpr_consent': profile.gdpr_consent,
                'gdpr_consent_date': profile.gdpr_consent_date.isoformat() if profile.gdpr_consent_date else None,
                'marketing_consent': profile.marketing_consent,
            }
        except CandidateProfile.DoesNotExist:
            pass

        # Rezyumelar
        data['resumes'] = []
        for r in Resume.objects.filter(user=user):
            data['resumes'].append({
                'title': r.title,
                'file': r.file.url if r.file else None,
                'created_at': r.created_at.isoformat(),
            })

        # Arizalar
        for app in Application.objects.filter(user=user):
            app_data = {
                'vacancy': app.vacancy.title,
                'status': app.get_status_display(),
                'created_at': app.created_at.isoformat(),
            }
            try:
                if app.interview:
                    app_data['interview'] = {
                        'date_time': app.interview.date_time.isoformat(),
                        'status': app.interview.get_status_display(),
                    }
            except Interview.DoesNotExist:
                pass
            data['applications'].append(app_data)

    elif user.role == 'employer':
        try:
            profile = user.employer_profile
            data['profile'] = {
                'company_name': profile.company_name,
                'stir': profile.stir,
                'company_address': profile.company_address,
                'company_phone': profile.company_phone,
                'responsible_full_name': profile.responsible_full_name,
                'gdpr_consent': profile.gdpr_consent,
                'gdpr_consent_date': profile.gdpr_consent_date.isoformat() if profile.gdpr_consent_date else None,
                'marketing_consent': profile.marketing_consent,
            }
        except EmployerProfile.DoesNotExist:
            pass

        # Vakansiyalar
        data['vacancies'] = []
        for v in Vacancy.objects.filter(employer=user):
            data['vacancies'].append({
                'title': v.title,
                'salary': v.salary,
                'location': v.location,
                'job_type': v.get_job_type_display(),
                'is_active': v.is_active,
                'created_at': v.created_at.isoformat(),
            })

    # Rozilik jurnalini qo'shish
    Consent.objects.create(
        user=user,
        consent_type='data_processing',
        consent_text="Foydalanuvchi o'z ma'lumotlarini eksport qildi (Data Portability).",
        ip_address=get_client_ip(request),
    )

    response = JsonResponse(data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="ishTopish_data_{user.username}.json"'
    return response


@login_required
def delete_account_view(request):
    """Hisobni butunlay o'chirish (GDPR — Right to Erasure)."""
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_delete', '')

        if confirm != 'DELETE':
            messages.error(request, "Tasdiqlash uchun 'DELETE' so'zini yozing.")
            return redirect('delete_account')

        if not request.user.check_password(password):
            messages.error(request, "Parol noto'g'ri!")
            return redirect('delete_account')

        user = request.user

        # Rozilik jurnalini qo'shish (o'chirilishidan oldin)
        Consent.objects.create(
            user=user,
            consent_type='gdpr',
            consent_text=f"Foydalanuvchi '{user.username}' o'z hisobini butunlay o'chirishni so'radi (Right to Erasure).",
            ip_address=get_client_ip(request),
        )

        # Foydalanuvchini chiqarish va o'chirish
        logout(request)
        user.delete()  # CASCADE orqali barcha bog'liq ma'lumotlar o'chiriladi

        messages.success(request, "Hisobingiz va barcha shaxsiy ma'lumotlaringiz muvaffaqiyatli o'chirildi.")
        return redirect('home')

    return render(request, 'gdpr/delete_account.html')


@login_required
@require_POST
def update_gdpr_consent(request):
    """GDPR va marketing roziligini yangilash."""
    user = request.user
    gdpr = 'gdpr_consent' in request.POST
    marketing = 'marketing_consent' in request.POST

    if user.role == 'candidate':
        profile, _ = CandidateProfile.objects.get_or_create(user=user)
    elif user.role == 'employer':
        profile, _ = EmployerProfile.objects.get_or_create(user=user)
    else:
        messages.error(request, "Noma'lum foydalanuvchi roli.")
        return redirect('home')

    profile.gdpr_consent = gdpr
    profile.marketing_consent = marketing
    if gdpr:
        profile.gdpr_consent_date = timezone.now()
    profile.save()

    # Rozilik jurnali
    Consent.objects.create(
        user=user,
        consent_type='gdpr',
        consent_text=f"GDPR roziligi: {'berildi' if gdpr else 'bekor qilindi'}. Marketing: {'berildi' if marketing else 'bekor qilindi'}.",
        ip_address=get_client_ip(request),
    )

    messages.success(request, "GDPR sozlamalari yangilandi.")

    if user.role == 'candidate':
        return redirect('candidate_profile')
    return redirect('edit_profile')


@require_POST
def cookie_consent_view(request):
    """Cookie roziligini qabul qilish (AJAX)."""
    response = JsonResponse({'status': 'ok'})
    response.set_cookie(
        'cookie_consent', 'accepted',
        max_age=365 * 24 * 60 * 60,  # 1 yil
        httponly=True,
        samesite='Lax',
    )
    return response