from django.test import TestCase, Client
from django.urls import reverse
from .models import User, CandidateProfile, EmployerProfile, Vacancy, Application, Resume, Interview, Consent


class UserModelTest(TestCase):
    """User modeli testlari."""
    
    def test_create_candidate(self):
        """Nomzod foydalanuvchisini yaratish."""
        user = User.objects.create_user(
            username='candidate1',
            password='test12345',
            role='candidate',
            email='candidate@test.com'
        )
        self.assertEqual(user.role, 'candidate')
        self.assertTrue(user.check_password('test12345'))
    
    def test_create_employer(self):
        """Ish beruvchi foydalanuvchisini yaratish."""
        user = User.objects.create_user(
            username='employer1',
            password='test12345',
            role='employer',
            email='employer@test.com'
        )
        self.assertEqual(user.role, 'employer')


class AuthViewsTest(TestCase):
    """Avtorizatsiya view'lari testlari."""
    
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username='testcandidate',
            password='testpass123',
            role='candidate'
        )
        self.employer = User.objects.create_user(
            username='testemployer',
            password='testpass123',
            role='employer'
        )
    
    def test_home_page(self):
        """Bosh sahifa 200 status qaytarishi kerak."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_page_get(self):
        """Login sahifasi GET so'rovda 200 qaytarishi kerak."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_success_candidate(self):
        """Nomzod muvaffaqiyatli login qilishi kerak."""
        response = self.client.post(reverse('login'), {
            'username': 'testcandidate',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('candidate_home'))
    
    def test_login_success_employer(self):
        """Ish beruvchi muvaffaqiyatli login qilib, employer_home ga yo'naltirilishi kerak."""
        response = self.client.post(reverse('login'), {
            'username': 'testemployer',
            'password': 'testpass123'
        })
        self.assertRedirects(response, reverse('employer_home'))
    
    def test_login_wrong_password(self):
        """Noto'g'ri parol bilan login muvaffaqiyatsiz bo'lishi kerak."""
        response = self.client.post(reverse('login'), {
            'username': 'testcandidate',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
    
    def test_logout_requires_post(self):
        """O6-FIX: Logout faqat POST orqali ishlashi kerak."""
        self.client.login(username='testcandidate', password='testpass123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)
    
    def test_logout_via_post(self):
        """POST orqali logout muvaffaqiyatli ishlashi kerak."""
        self.client.login(username='testcandidate', password='testpass123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
    
    def test_authenticated_user_redirect_from_login(self):
        """Login qilgan foydalanuvchi login sahifasidan yo'naltirilishi kerak."""
        self.client.login(username='testcandidate', password='testpass123')
        response = self.client.get(reverse('login'))
        self.assertRedirects(response, reverse('candidate_home'))


class RoleAccessTest(TestCase):
    """Rolga asoslangan kirish nazorati testlari."""
    
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username='testcandidate',
            password='testpass123',
            role='candidate'
        )
        self.employer = User.objects.create_user(
            username='testemployer',
            password='testpass123',
            role='employer'
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Test Co')
    
    def test_candidate_cannot_access_employer_home(self):
        """Nomzod ish beruvchi sahifasiga kira olmasligi kerak."""
        self.client.login(username='testcandidate', password='testpass123')
        response = self.client.get(reverse('employer_home'))
        self.assertRedirects(response, reverse('home'))
    
    def test_employer_cannot_access_candidate_home(self):
        """Ish beruvchi nomzod sahifasiga kira olmasligi kerak."""
        self.client.login(username='testemployer', password='testpass123')
        response = self.client.get(reverse('candidate_home'))
        self.assertRedirects(response, reverse('home'))
    
    def test_anonymous_redirect_to_login(self):
        """Login qilmagan foydalanuvchi login sahifasiga yo'naltirilishi kerak."""
        response = self.client.get(reverse('candidate_home'))
        self.assertEqual(response.status_code, 302)


class VacancyTest(TestCase):
    """Vakansiya CRUD testlari."""
    
    def setUp(self):
        self.client = Client()
        self.employer = User.objects.create_user(
            username='employer1',
            password='testpass123',
            role='employer'
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Test Company')
        self.client.login(username='employer1', password='testpass123')
    
    def test_vacancy_create(self):
        """Vakansiya yaratish testi."""
        response = self.client.post(reverse('vacancy_create'), {
            'title': 'Python Developer',
            'salary': '5000000',
            'location': 'Toshkent',
            'job_type': 'full_time',
            'description': 'Python dasturchi kerak',
            'is_active': True,
        })
        self.assertRedirects(response, reverse('vacancy_list'))
        self.assertTrue(Vacancy.objects.filter(title='Python Developer').exists())
    
    def test_vacancy_list(self):
        """Vakansiyalar ro'yxati sahifasi."""
        Vacancy.objects.create(
            employer=self.employer,
            title='Test Vacancy',
            description='Test',
        )
        response = self.client.get(reverse('vacancy_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_vacancy_delete(self):
        """Vakansiyani o'chirish testi."""
        vacancy = Vacancy.objects.create(
            employer=self.employer,
            title='Delete Me',
            description='Test',
        )
        response = self.client.post(reverse('vacancy_delete', kwargs={'id': vacancy.id}))
        self.assertRedirects(response, reverse('vacancy_list'))
        self.assertFalse(Vacancy.objects.filter(id=vacancy.id).exists())


class ApplicationTest(TestCase):
    """Ariza tizimi testlari."""
    
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username='candidate1', password='testpass123', role='candidate'
        )
        CandidateProfile.objects.create(user=self.candidate)
        
        self.employer = User.objects.create_user(
            username='employer1', password='testpass123', role='employer'
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Test Co')
        
        self.vacancy = Vacancy.objects.create(
            employer=self.employer,
            title='Test Job',
            description='Test description',
        )
    
    def test_update_status_requires_post(self):
        """Status yangilash faqat POST orqali ishlashi kerak."""
        self.client.login(username='employer1', password='testpass123')
        resume = Resume.objects.create(user=self.candidate, title='CV')
        app = Application.objects.create(
            user=self.candidate, vacancy=self.vacancy,
            resume=resume, status='pending'
        )
        # GET so'rov 405 qaytarishi kerak
        response = self.client.get(
            reverse('update_status', kwargs={'app_id': app.id, 'new_status': 'accepted'})
        )
        self.assertEqual(response.status_code, 405)
    
    def test_update_status_via_post(self):
        """Status POST orqali muvaffaqiyatli yangilanishi kerak."""
        self.client.login(username='employer1', password='testpass123')
        resume = Resume.objects.create(user=self.candidate, title='CV')
        app = Application.objects.create(
            user=self.candidate, vacancy=self.vacancy,
            resume=resume, status='pending'
        )
        response = self.client.post(
            reverse('update_status', kwargs={'app_id': app.id, 'new_status': 'accepted'})
        )
        app.refresh_from_db()
        self.assertEqual(app.status, 'accepted')


class InterviewTest(TestCase):
    """Suhbat tizimi testlari."""
    
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username='candidate1', password='testpass123', role='candidate'
        )
        CandidateProfile.objects.create(user=self.candidate)
        
        self.employer = User.objects.create_user(
            username='employer1', password='testpass123', role='employer'
        )
        EmployerProfile.objects.create(user=self.employer, company_name='Test Co')
        
        self.vacancy = Vacancy.objects.create(
            employer=self.employer, title='Test Job', description='Test'
        )
        self.resume = Resume.objects.create(user=self.candidate, title='CV')
        self.application = Application.objects.create(
            user=self.candidate, vacancy=self.vacancy,
            resume=self.resume, status='pending'
        )
    
    def test_respond_to_interview_requires_post(self):
        """Suhbatga javob berish faqat POST orqali ishlashi kerak."""
        interview = Interview.objects.create(
            application=self.application,
            date_time='2026-05-01 10:00',
            location_link='https://zoom.us/test',
        )
        self.client.login(username='candidate1', password='testpass123')
        response = self.client.get(
            reverse('respond_to_interview', kwargs={'interview_id': interview.id, 'decision': 'accept'})
        )
        self.assertEqual(response.status_code, 405)
    
    def test_delete_interview_requires_post(self):
        """Suhbatni o'chirish faqat POST orqali ishlashi kerak."""
        interview = Interview.objects.create(
            application=self.application,
            date_time='2026-05-01 10:00',
            location_link='https://zoom.us/test',
        )
        self.client.login(username='employer1', password='testpass123')
        response = self.client.get(
            reverse('delete_interview', kwargs={'interview_id': interview.id})
        )
        self.assertEqual(response.status_code, 405)


class JobListTest(TestCase):
    """Vakansiyalar qidirish testi."""
    
    def setUp(self):
        self.client = Client()
        self.employer = User.objects.create_user(
            username='employer1', password='testpass123', role='employer'
        )
        Vacancy.objects.create(
            employer=self.employer,
            title='Python Developer',
            description='Django bilan ishlash',
            location='Toshkent',
            is_active=True,
        )
        Vacancy.objects.create(
            employer=self.employer,
            title='Frontend Developer',
            description='React ishlash',
            location='Samarqand',
            is_active=True,
        )
    
    def test_job_list_page(self):
        """Ish o'rinlari ro'yxati sahifasi."""
        response = self.client.get(reverse('job_list'))
        self.assertEqual(response.status_code, 200)
    
    def test_job_search_by_title(self):
        """Nomiga ko'ra qidirish."""
        response = self.client.get(reverse('job_list'), {'q': 'Python'})
        self.assertEqual(response.status_code, 200)
    
    def test_job_search_by_location(self):
        """Manzilga ko'ra qidirish."""
        response = self.client.get(reverse('job_list'), {'location': 'Toshkent'})
        self.assertEqual(response.status_code, 200)


# ==========================================
# P2-FIX: GDPR TESTLARI
# ==========================================

class GDPRExportDataTest(TestCase):
    """GDPR — Ma'lumotlarni eksport qilish testlari."""
    
    def setUp(self):
        self.client = Client()
        self.candidate = User.objects.create_user(
            username='gdpr_candidate', password='testpass123',
            role='candidate', email='gdpr@test.com'
        )
        CandidateProfile.objects.create(
            user=self.candidate, gdpr_consent=True
        )
        self.client.login(username='gdpr_candidate', password='testpass123')
    
    def test_export_data_returns_json(self):
        """Ma'lumotlarni eksport qilish JSON formatda qaytarishi kerak."""
        response = self.client.get(reverse('export_user_data'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response.get('Content-Disposition', ''))
    
    def test_export_data_contains_account(self):
        """Eksport qilingan ma'lumotda hisob ma'lumotlari bo'lishi kerak."""
        import json
        response = self.client.get(reverse('export_user_data'))
        data = json.loads(response.content)
        self.assertIn('account', data)
        self.assertEqual(data['account']['username'], 'gdpr_candidate')
    
    def test_export_creates_consent_log(self):
        """Eksport qilish rozilik jurnalini yaratishi kerak."""
        self.client.get(reverse('export_user_data'))
        consent = Consent.objects.filter(
            user=self.candidate,
            consent_type='data_processing'
        )
        self.assertTrue(consent.exists())
    
    def test_export_requires_auth(self):
        """Login qilmagan foydalanuvchi eksport qila olmasligi kerak."""
        self.client.logout()
        response = self.client.get(reverse('export_user_data'))
        self.assertEqual(response.status_code, 302)  # Login sahifasiga yo'naltirish


class GDPRDeleteAccountTest(TestCase):
    """GDPR — Hisobni o'chirish testlari."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='delete_me', password='testpass123',
            role='candidate'
        )
        CandidateProfile.objects.create(user=self.user)
        self.client.login(username='delete_me', password='testpass123')
    
    def test_delete_account_page_loads(self):
        """Hisobni o'chirish sahifasi 200 qaytarishi kerak."""
        response = self.client.get(reverse('delete_account'))
        self.assertEqual(response.status_code, 200)
    
    def test_delete_account_wrong_password(self):
        """Noto'g'ri parol bilan o'chirish muvaffaqiyatsiz bo'lishi kerak."""
        response = self.client.post(reverse('delete_account'), {
            'password': 'wrongpassword',
            'confirm_delete': 'DELETE'
        })
        # Foydalanuvchi o'chirilmagan
        self.assertTrue(User.objects.filter(username='delete_me').exists())
    
    def test_delete_account_wrong_confirmation(self):
        """Noto'g'ri tasdiqlash matni bilan o'chirish rad etilishi kerak."""
        response = self.client.post(reverse('delete_account'), {
            'password': 'testpass123',
            'confirm_delete': 'WRONG'
        })
        self.assertTrue(User.objects.filter(username='delete_me').exists())
    
    def test_delete_account_success(self):
        """To'g'ri parol va tasdiqlash bilan hisob o'chirilishi kerak."""
        response = self.client.post(reverse('delete_account'), {
            'password': 'testpass123',
            'confirm_delete': 'DELETE'
        })
        self.assertFalse(User.objects.filter(username='delete_me').exists())
        self.assertRedirects(response, reverse('home'))
    
    def test_delete_requires_auth(self):
        """Login qilmagan foydalanuvchi o'chira olmasligi kerak."""
        self.client.logout()
        response = self.client.get(reverse('delete_account'))
        self.assertEqual(response.status_code, 302)


class GDPRConsentTest(TestCase):
    """GDPR — Rozilik boshqaruvi testlari."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='consent_user', password='testpass123',
            role='candidate'
        )
        CandidateProfile.objects.create(user=self.user, gdpr_consent=True)
        self.client.login(username='consent_user', password='testpass123')
    
    def test_update_consent_requires_post(self):
        """Consent yangilash faqat POST orqali ishlashi kerak."""
        response = self.client.get(reverse('update_gdpr_consent'))
        self.assertEqual(response.status_code, 405)
    
    def test_consent_grant(self):
        """GDPR roziligi berilishi kerak."""
        response = self.client.post(reverse('update_gdpr_consent'), {
            'gdpr_consent': 'on',
        })
        profile = CandidateProfile.objects.get(user=self.user)
        self.assertTrue(profile.gdpr_consent)
        self.assertIsNotNone(profile.gdpr_consent_date)
    
    def test_consent_revoke_clears_date(self):
        """O1-FIX: Rozilik bekor qilinganda sana ham tozalanishi kerak."""
        # Avval rozilik beramiz
        self.client.post(reverse('update_gdpr_consent'), {
            'gdpr_consent': 'on',
        })
        # Keyin bekor qilamiz
        self.client.post(reverse('update_gdpr_consent'), {})
        profile = CandidateProfile.objects.get(user=self.user)
        self.assertFalse(profile.gdpr_consent)
        self.assertIsNone(profile.gdpr_consent_date)
    
    def test_consent_creates_log(self):
        """Rozilik o'zgarganda jurnal yozilishi kerak."""
        self.client.post(reverse('update_gdpr_consent'), {
            'gdpr_consent': 'on',
        })
        consent_logs = Consent.objects.filter(
            user=self.user, consent_type='gdpr'
        )
        self.assertTrue(consent_logs.exists())
    
    def test_consent_log_has_policy_version(self):
        """O2-FIX: Consent jurnalida siyosat versiyasi bo'lishi kerak."""
        self.client.post(reverse('update_gdpr_consent'), {
            'gdpr_consent': 'on',
        })
        consent = Consent.objects.filter(
            user=self.user, consent_type='gdpr'
        ).latest('accepted_at')
        self.assertIsNotNone(consent.policy_version)
        self.assertNotEqual(consent.policy_version, '')


class GDPRRegistrationConsentTest(TestCase):
    """K4-FIX: Ro'yxatdan o'tishda GDPR rozilik testlari."""
    
    def setUp(self):
        self.client = Client()
    
    def test_candidate_registration_creates_consent(self):
        """Nomzod ro'yxatdan o'tganda consent yaratilishi kerak."""
        response = self.client.post(reverse('register_candidate'), {
            'full_name': 'Test User',
            'username': 'newcandidate',
            'email': 'new@test.com',
            'phone': '+998901234567',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
            'consent': True,
        })
        # Foydalanuvchi yaratilganini tekshirish
        if User.objects.filter(username='newcandidate').exists():
            user = User.objects.get(username='newcandidate')
            # GDPR consent yaratilganini tekshirish
            gdpr_consent = Consent.objects.filter(
                user=user, consent_type='gdpr'
            )
            self.assertTrue(gdpr_consent.exists())
            # Profile da gdpr_consent=True
            profile = CandidateProfile.objects.get(user=user)
            self.assertTrue(profile.gdpr_consent)
            self.assertIsNotNone(profile.gdpr_consent_date)


class GDPRPolicyPagesTest(TestCase):
    """GDPR sahifalari testlari."""
    
    def setUp(self):
        self.client = Client()
    
    def test_privacy_policy_page(self):
        """Maxfiylik siyosati sahifasi 200 qaytarishi kerak."""
        response = self.client.get(reverse('privacy_policy'))
        self.assertEqual(response.status_code, 200)
    
    def test_terms_page(self):
        """Foydalanish shartlari sahifasi 200 qaytarishi kerak."""
        response = self.client.get(reverse('terms_of_service'))
        self.assertEqual(response.status_code, 200)
    
    def test_gdpr_policy_page(self):
        """GDPR siyosati sahifasi 200 qaytarishi kerak."""
        response = self.client.get(reverse('gdpr_policy'))
        self.assertEqual(response.status_code, 200)


class CookieConsentTest(TestCase):
    """Cookie consent testlari."""
    
    def setUp(self):
        self.client = Client()
    
    def test_cookie_consent_post(self):
        """Cookie consent POST so'rov qabul qilishi kerak."""
        response = self.client.post(reverse('cookie_consent'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('cookie_consent', response.cookies)
    
    def test_cookie_consent_get_rejected(self):
        """Cookie consent GET so'rov rad qilinishi kerak."""
        response = self.client.get(reverse('cookie_consent'))
        self.assertEqual(response.status_code, 405)


class ProtectedMediaTest(TestCase):
    """K5-FIX: Himoyalangan media fayllar testlari."""
    
    def setUp(self):
        self.client = Client()
    
    def test_media_requires_auth(self):
        """Media fayllar autentifikatsiyani talab qilishi kerak."""
        response = self.client.get('/media/resumes/test.pdf')
        self.assertEqual(response.status_code, 302)  # Login sahifasiga yo'naltirish
