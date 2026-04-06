from django.test import TestCase, Client
from django.urls import reverse
from .models import User, CandidateProfile, EmployerProfile, Vacancy, Application, Resume, Interview


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
    
    def test_logout(self):
        """Logout muvaffaqiyatli ishlashi kerak."""
        self.client.login(username='testcandidate', password='testpass123')
        response = self.client.get(reverse('logout'))
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
