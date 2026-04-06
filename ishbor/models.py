from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone




# =========================
# USER MODEL
# =========================
class User(AbstractUser):
    ROLE_CHOICES = (
        ('candidate', 'Ish izlovchi'),
        ('employer', 'Ish beruvchi'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

# =========================
# CANDIDATE PROFILE
# =========================



class CandidateProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    image = models.ImageField(upload_to='candidates/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(max_length=500, blank=True) # O'zi haqida qisqacha
    skills = models.CharField(max_length=255, blank=True) # Ko'nikmalar (Python, Java va hokazo)
    
    # GDPR va Nizomlar
    gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_date = models.DateTimeField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

class Experience(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='experiences')
    company = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

class Certificate(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='certificates')
    name = models.CharField(max_length=150)
    file = models.FileField(upload_to='certificates/')
    issued_date = models.DateField()


class Resume(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=100) # Masalan: "Python dasturchi rezyumesi"
    file = models.FileField(upload_to='resumes/') # PDF yoki DOCX uchun
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

# =========================
# EMPLOYER PROFILE
# =========================
class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company_name = models.CharField(max_length=255)
    stir = models.CharField(max_length=20)
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    company_address = models.TextField()
    company_phone = models.CharField(max_length=20)
    responsible_full_name = models.CharField(max_length=150)

    # GDPR va Nizomlar
    gdpr_consent = models.BooleanField(default=False)
    gdpr_consent_date = models.DateTimeField(null=True, blank=True)
    marketing_consent = models.BooleanField(default=False)

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

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

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
    consent_text = models.TextField()
    is_active = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-accepted_at']

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
    
    cover_letter = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Suhbat: {self.application.user.username} - {self.date_time}"