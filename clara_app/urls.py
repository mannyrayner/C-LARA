

from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='clara_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),  
    path('home/', views.home, name='home'),  
    path('profile/', views.profile, name='profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('add_credit/', views.add_credit, name='add_credit'),
    path('credit_balance/', views.credit_balance, name='credit_balance'),
    path('manage_language_masters/', views.manage_language_masters, name='manage_language_masters'),
    path('remove_language_master/<int:pk>/', views.remove_language_master, name='remove_language_master'),
    path('edit_prompt/', views.edit_prompt, name='edit_prompt'),
    path('register_content/', views.register_content, name='register_content'),
    path('content_success/', views.content_success, name='content_success'),
    path('content_list/', views.content_list, name='content_list'),
    path('content/<int:content_id>/', views.content_detail, name='content_detail'),
    path('create_project/', views.create_project, name='create_project'),
    path('project_list/', views.project_list, name='project_list'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('project/<int:project_id>/manage_project_members/', views.manage_project_members, name='manage_project_members'),
    path('project/<int:permission_id>/remove_project_member/', views.remove_project_member, name='remove_project_member'),
    path('project/<int:project_id>/delete/', views.delete_project, name='delete_project'),  
    path('project/<int:project_id>/clone_project/', views.clone_project, name='clone_project'),  
    path('project/<int:project_id>/create_plain_text/', views.create_plain_text, name='create_plain_text'),
    path('project/<int:project_id>/create_summary/', views.create_summary, name='create_summary'),
    path('project/<int:project_id>/create_segmented_text/', views.create_segmented_text, name='create_segmented_text'),
    path('project/<int:project_id>/create_glossed_text/', views.create_glossed_text, name='create_glossed_text'),
    path('project/<int:project_id>/create_lemma_tagged_text/', views.create_lemma_tagged_text, name='create_lemma_tagged_text'),
    path('project/<int:project_id>/create_lemma_and_gloss_tagged_text/', views.create_lemma_and_gloss_tagged_text, name='create_lemma_and_gloss_tagged_text'),
    path('project/<int:project_id>/history/', views.project_history, name='project_history'),
    path('project/<int:project_id>/render_text_start/', views.render_text_start, name='render_text_start'),
    path('project/<int:project_id>/render_text_status/<str:task_id>/<str:report_id>/', views.render_text_status, name='render_text_status'),
    path('project/<int:project_id>/render_text_monitor/<str:task_id>/<str:report_id>/', views.render_text_monitor, name='render_text_monitor'),
    path('project/<int:project_id>/render_text_complete/<str:status>/', views.render_text_complete, name='render_text_complete'),
    path('project/<int:project_id>/generate_text_status/<str:report_id>/', views.generate_text_status, name='generate_text_status'),
    path('project/<int:project_id>/generate_text_monitor/<str:version>/<str:report_id>/', views.generate_text_monitor, name='generate_text_monitor'),
    path('project/<int:project_id>/generate_text_complete/<str:version>/<str:status>/', views.generate_text_complete, name='generate_text_complete'),
    path('project/<int:project_id>/register_project_content/', views.register_project_content, name='register_project_content'),
    path('projects/<int:project_id>/compare_versions/', views.compare_versions, name='compare_versions'),
    path('projects/<int:project_id>/metadata/<str:version>/', views.get_metadata_for_version, name='get_metadata_for_version'),
    path('rendered_texts/<int:project_id>/static/<path:filename>', views.serve_rendered_text_static, name='serve_rendered_text'),
    path('rendered_texts/<int:project_id>/multimedia/<path:filename>', views.serve_rendered_text_multimedia, name='serve_rendered_text'),
    path('rendered_texts/<int:project_id>/<path:filename>', views.serve_rendered_text, name='serve_rendered_text'),
    path('serve_zipfile/<int:project_id>/', views.serve_zipfile, name='serve_zipfile'),
]

