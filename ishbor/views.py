from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.http import JsonResponse, FileResponse, Http404
from django.utils import timezone
from django.conf import settings as django_settings
from functools import wraps
import json
import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# K-PDF-FIX: Arial fontini ro'yxatdan o'tkazish (Unicode/O'zbek tili uchun)
try:
    pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
    FONT_NAME = 'Arial'
except Exception:
    FONT_NAME = 'Helvetica'

from .forms import (
    RoleChooseForm, CandidateRegisterForm, 
    EmployerRegisterForm, VacancyForm, ApplicationForm, EmployerProfileForm,
    CandidateProfileForm, validate_resume_file
)
from .models import (
    CandidateProfile, EmployerProfile, Consent, 
    Vacancy, Application, Resume, Interview, User
)
from .decorators import rate_limit


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

@rate_limit(key_prefix='login')  # K7-FIX: Brute force himoyasi
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

@require_POST  # O6-FIX: Logout faqat POST orqali — CSRF himoyasi
def logout_view(request):
    """Logout — faqat POST so'rov orqali."""
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
@rate_limit(key_prefix='register')  # K7-FIX: Ro'yxatdan o'tish uchun rate limit
def register_candidate(request):
    form = CandidateRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        # K4-FIX: gdpr_consent va gdpr_consent_date to'g'ri o'rnatiladi
        CandidateProfile.objects.create(
            user=user, 
            phone=user.phone,
            gdpr_consent=True,
            gdpr_consent_date=timezone.now()
        )
        # K4-FIX: Aniq rozilik matni va turi bilan Consent yaratish
        Consent.objects.create(
            user=user,
            consent_type='gdpr',
            consent_text="Foydalanuvchi ro'yxatdan o'tishda GDPR qoidalari asosida shaxsiy ma'lumotlarini "
                         "qayta ishlashga rozilik berdi.",
            ip_address=get_client_ip(request),
            policy_version=getattr(django_settings, 'GDPR_POLICY_VERSION', '1.0'),
        )
        Consent.objects.create(
            user=user,
            consent_type='registration',
            consent_text="Ish izlovchi sifatida ro'yxatdan o'tish roziligi.",
            ip_address=get_client_ip(request),
            policy_version=getattr(django_settings, 'GDPR_POLICY_VERSION', '1.0'),
        )
        
        login(request, user)
        res = redirect("candidate_home")
        res.set_cookie("gdpr_consent", "accepted", max_age=2592000, httponly=True, samesite='Lax')
        return res
    return render(request, "register_candidate.html", {"form": form})

@transaction.atomic
@rate_limit(key_prefix='register')  # K7-FIX: Ro'yxatdan o'tish uchun rate limit
def register_employer(request):
    form = EmployerRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        # K4-FIX: gdpr_consent va gdpr_consent_date to'g'ri o'rnatiladi
        EmployerProfile.objects.create(
            user=user, 
            company_name=form.cleaned_data["company_name"],
            stir=form.cleaned_data["stir"],
            company_address=form.cleaned_data["company_address"],
            company_phone=form.cleaned_data["company_phone"],
            responsible_full_name=form.cleaned_data["responsible_full_name"],
            gdpr_consent=True,
            gdpr_consent_date=timezone.now()
        )
        # K4-FIX: Aniq rozilik matni va turi bilan Consent yaratish
        Consent.objects.create(
            user=user,
            consent_type='gdpr',
            consent_text="Ish beruvchi ro'yxatdan o'tishda GDPR qoidalari asosida kompaniya "
                         "ma'lumotlarini qayta ishlashga rozilik berdi.",
            ip_address=get_client_ip(request),
            policy_version=getattr(django_settings, 'GDPR_POLICY_VERSION', '1.0'),
        )
        Consent.objects.create(
            user=user,
            consent_type='registration',
            consent_text="Ish beruvchi sifatida ro'yxatdan o'tish roziligi.",
            ip_address=get_client_ip(request),
            policy_version=getattr(django_settings, 'GDPR_POLICY_VERSION', '1.0'),
        )
        
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
            # O4-FIX: Ariza topshirishda rozilik jurnalga yoziladi
            Consent.objects.create(
                user=request.user,
                consent_type='data_processing',
                consent_text=f"Foydalanuvchi '{vacancy.title}' vakansiyasiga ariza topshirishda "
                             f"shaxsiy ma'lumotlari va rezyumesi ish beruvchi tomonidan "
                             f"ko'rib chiqilishiga rozilik berdi.",
                ip_address=get_client_ip(request),
                policy_version=getattr(django_settings, 'GDPR_POLICY_VERSION', '1.0'),
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
            # P1-FIX: Forma orqali validatsiya qilinadi
            form = CandidateProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Profil yangilandi.")
            else:
                messages.error(request, "Ma'lumotlarda xatolik bor.")
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

    # ==========================================
    # PDF GENERATION (K-PDF-FIX)
    # ==========================================
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    # Maxsus stillar
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontName=FONT_NAME, fontSize=20, alignment=1, spaceAfter=20)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontName=FONT_NAME, fontSize=14, spaceBefore=15, spaceAfter=10, textColor=colors.HexColor('#2c3e50'))
    normal_style = ParagraphStyle('NormalText', parent=styles['Normal'], fontName=FONT_NAME, fontSize=11, leading=14, spaceAfter=6)
    label_style = ParagraphStyle('Label', parent=normal_style, fontName=f"{FONT_NAME}", fontWeight='bold')

    elements = []

    # Sarlavha
    elements.append(Paragraph(f"Shaxsiy ma'lumotlar hisoboti", title_style))
    elements.append(Paragraph(f"Foydalanuvchi: {user.username}", normal_style))
    elements.append(Paragraph(f"Sana: {timezone.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
    elements.append(Spacer(1, 20))

    # 1. Hisob ma'lumotlari
    elements.append(Paragraph("1. Hisob ma'lumotlari", heading_style))
    elements.append(Paragraph(f"<b>F.I.SH:</b> {user.first_name} {user.last_name}", normal_style))
    elements.append(Paragraph(f"<b>Email:</b> {user.email}", normal_style))
    elements.append(Paragraph(f"<b>Telefon:</b> {user.phone or 'Kiritilmagan'}", normal_style))
    elements.append(Paragraph(f"<b>Rol:</b> {user.get_role_display()}", normal_style))
    elements.append(Paragraph(f"<b>Ro'yxatdan o'tgan sana:</b> {user.date_joined.strftime('%d.%m.%Y')}", normal_style))

    # 2. Profil ma'lumotlari
    if 'profile' in data:
        elements.append(Paragraph("2. Profil ma'lumotlari", heading_style))
        p = data['profile']
        if user.role == 'candidate':
            elements.append(Paragraph(f"<b>Biografiya:</b> {p.get('bio', '—')}", normal_style))
            elements.append(Paragraph(f"<b>Ko'nikmalar:</b> {p.get('skills', '—')}", normal_style))
        else:
            elements.append(Paragraph(f"<b>Kompaniya nomi:</b> {p.get('company_name', '—')}", normal_style))
            elements.append(Paragraph(f"<b>STIR:</b> {p.get('stir', '—')}", normal_style))
            elements.append(Paragraph(f"<b>Manzil:</b> {p.get('company_address', '—')}", normal_style))
            elements.append(Paragraph(f"<b>Kompaniya telefoni:</b> {p.get('company_phone', '—')}", normal_style))
            elements.append(Paragraph(f"<b>Mas'ul shaxs:</b> {p.get('responsible_full_name', '—')}", normal_style))

    # 3. Rezyumelar (nomzod bo'lsa)
    if 'resumes' in data and data['resumes']:
        elements.append(Paragraph("3. Rezyumelar", heading_style))
        for r in data['resumes']:
            elements.append(Paragraph(f"• {r['title']} ({r['created_at'][:10]})", normal_style))

    # 4. Arizalar / Vakansiyalar
    if user.role == 'candidate' and data['applications']:
        elements.append(Paragraph("4. Topshirilgan arizalar", heading_style))
        for app in data['applications']:
            elements.append(Paragraph(f"• <b>{app['vacancy']}</b> - Holat: {app['status']} ({app['created_at'][:10]})", normal_style))
            if 'interview' in app:
                elements.append(Paragraph(f"  <i>Suhbat: {app['interview']['date_time'][:16]} - {app['interview']['status']}</i>", normal_style))
    
    elif user.role == 'employer' and data['vacancies']:
        elements.append(Paragraph("4. E'lon qilingan vakansiyalar", heading_style))
        for v in data['vacancies']:
            elements.append(Paragraph(f"• <b>{v['title']}</b> - Maosh: {v['salary']} ({v['created_at'][:10]})", normal_style))

    # 5. Roziliklar (GDPR)
    if data['consents']:
        elements.append(Paragraph("5. Roziliklar tarixi", heading_style))
        for c in data['consents']:
            elements.append(Paragraph(f"• {c['type']}: {c['accepted_at'][:16]} - {'Faol' if c['is_active'] else 'Noactive'}", normal_style))

    # PDFni yakunlash
    doc.build(elements)
    buffer.seek(0)
    
    response = FileResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ishTopish_data_{user.username}.pdf"'
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
    # O1-FIX: Rozilik berilganda sana o'rnatiladi, bekor qilinganda None qilinadi
    if gdpr:
        profile.gdpr_consent_date = timezone.now()
    else:
        profile.gdpr_consent_date = None  # Eski sana saqlanib qolmasligi uchun
    profile.save()

    # Rozilik jurnali — O2-FIX: policy_version qo'shildi
    Consent.objects.create(
        user=user,
        consent_type='gdpr',
        consent_text=f"GDPR roziligi: {'berildi' if gdpr else 'bekor qilindi'}. Marketing: {'berildi' if marketing else 'bekor qilindi'}.",
        ip_address=get_client_ip(request),
        policy_version=getattr(django_settings, 'GDPR_POLICY_VERSION', '1.0'),
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


# ==========================================
# K5-FIX: HIMOYALANGAN MEDIA FAYLLAR
# ==========================================
@login_required
def serve_protected_media(request, path):
    """Media fayllarni faqat autentifikatsiyadan o'tgan foydalanuvchilarga ko'rsatish."""
    file_path = os.path.join(django_settings.MEDIA_ROOT, path)
    
    if not os.path.exists(file_path):
        raise Http404("Fayl topilmadi.")
    
    # Rezyume fayllarni faqat egasi yoki tegishli ish beruvchi ko'ra oladi
    if path.startswith('resumes/'):
        # Fayl egasi
        is_owner = Resume.objects.filter(user=request.user, file=path).exists()
        # Ish beruvchi — faqat ariza yuborilgan bo'lsa
        is_employer = False
        if request.user.role == 'employer':
            is_employer = Application.objects.filter(
                resume__file=path,
                vacancy__employer=request.user
            ).exists()
        # Admin
        is_admin = request.user.is_staff
        
        if not (is_owner or is_employer or is_admin):
            messages.error(request, "Ushbu faylga kirish huquqingiz yo'q.")
            return redirect('home')
    
    return FileResponse(open(file_path, 'rb'))