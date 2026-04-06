from django.urls import path
from .views import (choose_role, register_candidate, register_employer,
                    apply_for_job, employer_applications_list, update_application_status, edit_employer_profile, vacancy_detail,
                    job_list)
from .views import (login_view, logout_view, candidate_home, employer_home, home_views,
                    vacancy_create, vacancy_list, vacancy_update, vacancy_delete, candidate_profile_view,
                    resume_create, resume_delete, schedule_interview, respond_to_interview, edit_interview, delete_interview)
from .views import (
    privacy_policy_view, terms_of_service_view, gdpr_policy_view,
    export_user_data, delete_account_view, update_gdpr_consent, cookie_consent_view
)

urlpatterns = [

    path('', home_views, name='home'),
    path('register/', choose_role, name='choose_role'),
    path('register/candidate/', register_candidate, name='register_candidate'),
    path('register/employer/', register_employer, name='register_employer'),

    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    path("candidate/home/", candidate_home, name="candidate_home"),
    path("employer/home/", employer_home, name="employer_home"),

    path("employer/vacancies/", vacancy_list, name="vacancy_list"),
    path("employer/vacancy/create/", vacancy_create, name="vacancy_create"),
    path("employer/vacancy/update/<int:id>/", vacancy_update, name="vacancy_update"),
    path("employer/vacancy/delete/<int:id>/", vacancy_delete, name="vacancy_delete"),

    path('vacancy/<int:vacancy_id>/apply/', apply_for_job, name='apply_for_job'),
    path('employer/applications/', employer_applications_list, name='employer_applications_list'),
    path('employer/applications/<int:app_id>/update/<str:new_status>/', update_application_status, name='update_status'),

    path('employer/profile/edit/', edit_employer_profile, name='edit_profile'),
    #candidate
    path('jobs/', job_list, name='job_list'),
    path('vacancy/<int:pk>/', vacancy_detail, name='vacancy_detail'),

    path('candidate/profile/', candidate_profile_view, name='candidate_profile'),
    path('candidate/resume/create/', resume_create, name='resume_create'),
    path('candidate/resume/<int:id>/delete/', resume_delete, name='resume_delete'),

    path('employer/schedule-interview/<int:app_id>/', schedule_interview, name='schedule_interview'),
    path('candidate/interview-respond/<int:interview_id>/<str:decision>/', respond_to_interview, name='respond_to_interview'),

    path('interview/edit/<int:interview_id>/', edit_interview, name='edit_interview'),
    path('interview/delete/<int:interview_id>/', delete_interview, name='delete_interview'),

    # GDPR sahifalari
    path('privacy/', privacy_policy_view, name='privacy_policy'),
    path('terms/', terms_of_service_view, name='terms_of_service'),
    path('gdpr/', gdpr_policy_view, name='gdpr_policy'),

    # GDPR funksional sahifalari
    path('account/export-data/', export_user_data, name='export_user_data'),
    path('account/delete/', delete_account_view, name='delete_account'),
    path('account/gdpr-settings/', update_gdpr_consent, name='update_gdpr_consent'),
    path('cookie-consent/', cookie_consent_view, name='cookie_consent'),
]