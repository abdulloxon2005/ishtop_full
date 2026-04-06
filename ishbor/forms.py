import os
from django import forms
from django.conf import settings
from .models import User, Vacancy, Application, EmployerProfile, Resume


# Bootstrap klasslarini avtomatik qo'shish uchun Mixin
class BootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.RadioSelect) and not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-control'})

# ======================
# ROLE FORM
# ======================
class RoleChooseForm(forms.Form):
    role = forms.ChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Siz kimsiz?"
    )

# ======================
# CANDIDATE FORM
# ======================
class CandidateRegisterForm(BootstrapMixin, forms.ModelForm):
    full_name = forms.CharField(max_length=150, label="To'liq ismingiz")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Parol")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Parolni takrorlang")
    consent = forms.BooleanField(label="Rozilik beraman", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'phone']

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 != p2:
            raise forms.ValidationError("Parollar mos emas!")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "candidate"
        user.set_password(self.cleaned_data["password1"])
        
        # full_name ni first_name va last_name ga ajratib saqlash
        full_name = self.cleaned_data.get("full_name", "").strip()
        if full_name:
            parts = full_name.split(maxsplit=1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
        
        if commit:
            user.save()
        return user

# ======================
# EMPLOYER FORM
# ======================
class EmployerRegisterForm(BootstrapMixin, forms.ModelForm):
    company_name = forms.CharField(label="Kompaniya nomi")
    stir = forms.CharField(label="STIR (INN)")
    company_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), label="Kompaniya manzili")
    company_phone = forms.CharField(label="Kompaniya telefon raqami")
    responsible_full_name = forms.CharField(label="Mas'ul shaxs F.I.Sh")
    
    password1 = forms.CharField(widget=forms.PasswordInput, label="Parol")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Parolni takrorlang")
    consent = forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'phone']

    def clean_stir(self):
        stir = self.cleaned_data.get("stir")
        if not stir.isdigit():
            raise forms.ValidationError("STIR faqat raqamlardan iborat bo'lishi kerak")
        return stir

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 != p2:
            raise forms.ValidationError("Parollar mos emas!")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "employer"
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

# ======================
# VACANCY FORM
# ======================

class VacancyForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Vacancy
        fields = [
            "title", "salary", "location", "job_type",
            "description", "responsibilities", "requirements", 
            "benefits", "deadline", "is_active"
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'responsibilities': forms.Textarea(attrs={'rows': 3}),
            'requirements': forms.Textarea(attrs={'rows': 3}),
            'benefits': forms.Textarea(attrs={'rows': 2}),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ApplicationForm(forms.ModelForm):
    # GDPR uchun rozilik chekboxi
    gdpr_consent = forms.BooleanField(
        required=True,
        label="Men shaxsiy ma'lumotlarim (CV) qayta ishlanishiga va saqlanishiga roziman.",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Application
        # 'cv_file' o'rniga 'resume' va 'cover_letter' ishlatiladi
        fields = ['resume', 'cover_letter']
        widgets = {
            'resume': forms.Select(attrs={'class': 'form-select'}), # Rezyumeni tanlash uchun dropdown
            'cover_letter': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Nega aynan siz? (Ixtiyoriy)', 
                'class': 'form-control'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Bu qism faqat joriy foydalanuvchining rezyumelarini ko'rsatish uchun kerak
        user = kwargs.pop('user', None)
        super(ApplicationForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['resume'].queryset = Resume.objects.filter(user=user)


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ['company_name', 'logo', 'stir', 'company_address', 'company_phone', 'responsible_full_name']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'stir': forms.TextInput(attrs={'class': 'form-control'}),
            'company_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'company_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'responsible_full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
        }


def validate_resume_file(file):
    """Resume faylini tekshirish — faqat ruxsat berilgan formatlar."""
    ext = os.path.splitext(file.name)[1].lower()
    allowed = getattr(settings, 'ALLOWED_RESUME_EXTENSIONS', ['.pdf', '.doc', '.docx'])
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)
    
    if ext not in allowed:
        raise forms.ValidationError(
            f"Faqat {', '.join(allowed)} formatdagi fayllar ruxsat etilgan."
        )
    if file.size > max_size:
        raise forms.ValidationError(
            f"Fayl hajmi {max_size // (1024*1024)} MB dan oshmasligi kerak."
        )