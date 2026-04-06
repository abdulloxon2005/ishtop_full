from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, CandidateProfile, EmployerProfile, 
    Vacancy, Application, Resume, Interview, 
    Consent, Experience, Certificate
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'phone', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('username', 'email', 'phone')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Qo\'shimcha', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Qo\'shimcha', {'fields': ('role', 'phone')}),
    )


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'gdpr_consent', 'marketing_consent', 'gdpr_consent_date', 'updated_at')
    list_filter = ('gdpr_consent', 'marketing_consent')
    search_fields = ('user__username', 'phone')


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'user', 'stir', 'company_phone', 'gdpr_consent', 'marketing_consent')
    list_filter = ('gdpr_consent', 'marketing_consent')
    search_fields = ('company_name', 'stir', 'user__username')


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer', 'salary', 'location', 'job_type', 'is_active', 'created_at')
    list_filter = ('job_type', 'is_active', 'created_at')
    search_fields = ('title', 'description')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'vacancy', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'vacancy__title')


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'created_at', 'updated_at')
    search_fields = ('user__username', 'title')


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('application', 'date_time', 'status', 'created_at')
    list_filter = ('status', 'created_at')


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ('user', 'consent_type', 'is_active', 'ip_address', 'accepted_at')
    list_filter = ('consent_type', 'is_active', 'accepted_at')
    search_fields = ('user__username', 'consent_text')
    readonly_fields = ('accepted_at', 'ip_address')


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('profile', 'company', 'position', 'start_date', 'end_date')
    search_fields = ('company', 'position')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('profile', 'name', 'issued_date')
    search_fields = ('name',)
