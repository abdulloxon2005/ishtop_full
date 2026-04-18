from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import os


def upload_to_candidates(instance, filename):
    """UUID asosida nomzod rasmi uchun yo'l."""
    ext = os.path.splitext(filename)[1].lower()
    return f'candidates/{uuid.uuid4().hex}{ext}'


def upload_to_certificates(instance, filename):
    """UUID asosida sertifikat fayli uchun yo'l."""
    ext = os.path.splitext(filename)[1].lower()
    return f'certificates/{uuid.uuid4().hex}{ext}'


def upload_to_resumes(instance, filename):
    """UUID asosida rezyume fayli uchun yo'l."""
    ext = os.path.splitext(filename)[1].lower()
    return f'resumes/{uuid.uuid4().hex}{ext}'


def upload_to_company_logos(instance, filename):
    """UUID asosida kompaniya logotipi uchun yo'l."""
    ext = os.path.splitext(filename)[1].lower()
    return f'company_logos/{uuid.uuid4().hex}{ext}'




# =========================
# USER MODEL
# =========================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('candidate', 'Ish izlovchi'),
        ('employer', 'Ish beruvchi'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="Rol")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefon raqami")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

# =========================
# CANDIDATE PROFILE
# =========================



class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    image = models.ImageField(upload_to=upload_to_candidates, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(max_length=500, blank=True) # O'zi haqida qisqacha
    skills = models.CharField(max_length=255, blank=True) # Ko'nikmalar (Python, Java va hokazo)
    
    # GDPR va Nizomlar
    gdpr_consent = models.BooleanField(default=False, verbose_name="GDPR roziligi")
    gdpr_consent_date = models.DateTimeField(null=True, blank=True, verbose_name="GDPR rozilik sanasi")
    marketing_consent = models.BooleanField(default=False, verbose_name="Marketing roziligi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Nomzod profili"
        verbose_name_plural = "Nomzodlar profillari"

class Experience(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='experiences')
    company = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    end_date = models.DateField(null=True, blank=True, verbose_name="Tugash sanasi")
    description = models.TextField(blank=True, verbose_name="Tavsif")

    class Meta:
        verbose_name = "Tajriba"
        verbose_name_plural = "Tajribalar"

class Certificate(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='certificates')
    name = models.CharField(max_length=150)
    file = models.FileField(upload_to=upload_to_certificates, verbose_name="Fayl")
    issued_date = models.DateField(verbose_name="Berilgan sana")

    class Meta:
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikatlar"


class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=100, verbose_name="Sarlavha") # Masalan: "Python dasturchi rezyumesi"
    file = models.FileField(upload_to=upload_to_resumes, verbose_name="Fayl") # PDF yoki DOCX uchun
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Rezyume"
        verbose_name_plural = "Rezyumelar"

    def __str__(self):
        return f"{self.user.username} - {self.title}"

# =========================
# EMPLOYER PROFILE
# =========================
class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=255)
    stir = models.CharField(max_length=20)
    logo = models.ImageField(upload_to=upload_to_company_logos, null=True, blank=True)
    company_address = models.TextField()
    company_phone = models.CharField(max_length=20)
    responsible_full_name = models.CharField(max_length=150)

    # GDPR va Nizomlar
    gdpr_consent = models.BooleanField(default=False, verbose_name="GDPR roziligi")
    gdpr_consent_date = models.DateTimeField(null=True, blank=True, verbose_name="GDPR rozilik sanasi")
    marketing_consent = models.BooleanField(default=False, verbose_name="Marketing roziligi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Ish beruvchi profili"
        verbose_name_plural = "Ish beruvchilar profillari"

    def __str__(self):
        return self.company_name

# =========================
# VACANCY MODEL
# =========================
class Vacancy(models.Model):
    class JobType(models.TextChoices):
        FULL_TIME = 'full_time', 'To‘liq stavka'
        PART_TIME = 'part_time', 'Yarim stavka'
        REMOTE = 'remote', 'Masofaviy'

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='vacancies'
    )
    title = models.CharField(max_length=255)
    salary = models.CharField(max_length=100)
    location = models.CharField(max_length=255)
    job_type = models.CharField(
        max_length=50,
        choices=JobType.choices,
        default=JobType.FULL_TIME
    )
    
    # Batafsil ma'lumotlar
    description = models.TextField()
    responsibilities = models.TextField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    benefits = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True, verbose_name="Faol holatda")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    deadline = models.DateField(null=True, blank=True, verbose_name="Oxirgi muddat")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Vakansiya"
        verbose_name_plural = "Vakansiyalar"

    def __str__(self):
        return self.title

# =========================
# GDPR CONSENT
# =========================
class Consent(models.Model):
    CONSENT_TYPES = [
        ('registration', "Ro'yxatdan o'tish roziligi"),
        ('gdpr', 'GDPR roziligi'),
        ('marketing', 'Marketing roziligi'),
        ('data_processing', "Ma'lumotlarni qayta ishlash roziligi"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consents')
    consent_type = models.CharField(max_length=30, choices=CONSENT_TYPES, default='registration')
    policy_version = models.CharField(max_length=10, default='1.0', verbose_name="Siyosat versiyasi")
    consent_text = models.TextField()
    is_active = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP manzil")
    accepted_at = models.DateTimeField(auto_now_add=True, verbose_name="Qabul qilingan vaqt")

    class Meta:
        ordering = ['-accepted_at']
        verbose_name = "Rozilik (Consent)"
        verbose_name_plural = "Roziliklar (Consents)"

    def __str__(self):
        return f"{self.user.username} — {self.get_consent_type_display()}"
    


class Application(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('reviewed', 'Ko\'rib chiqildi'),
        ('accepted', 'Qabul qilindi'),
        ('rejected', 'Rad etildi'),
    ]

    vacancy = models.ForeignKey('Vacancy', on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # cv_file o'rniga Resume modeliga bog'laymiz
    resume = models.ForeignKey(Resume, on_delete=models.SET_NULL, null=True, blank=True)
    
    cover_letter = models.TextField(blank=True, null=True, verbose_name="Qo'shimcha xat (Cover Letter)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holat")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Ariza"
        verbose_name_plural = "Arizalar"

    def __str__(self):
        return f"{self.user.username} - {self.vacancy.title}"
    
class Interview(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('accepted', 'Nomzod qabul qildi'),
        ('rejected', 'Nomzod rad etdi'),
    ]
    
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='interview')
    date_time = models.DateTimeField(verbose_name="Suhbat vaqti")
    location_link = models.URLField(max_length=500, verbose_name="Suhbat manzili yoki Link (Zoom/Google Meet)")
    notes = models.TextField(blank=True, null=True, verbose_name="Qo'shimcha eslatmalar")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Suhbat"
        verbose_name_plural = "Suhbatlar"

    def __str__(self):
        return f"Suhbat: {self.application.user.username} - {self.date_time}"