

from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from . import views
from . import accounts_views
from . import home_views
from . import profile_views
from . import users_and_friends_views
from . import update_feed_views
from . import user_config_views
from . import task_update_views
from . import admin_permission_views
from . import credit_views
from . import delete_tts_views
from . import content_views
from . import language_masters_views
from . import funding_requests_views
from . import activity_tracker_views
from . import annotation_prompts_views
from . import phonetic_lexicon_views
from . import simple_clara_views
from . import create_project_views
from . import manipulate_project_views
from . import export_zipfile_views
from . import annotation_views
from . import human_audio_views
from . import images_v1_views
from . import images_v2_views
from . import save_page_texts_multiple_views
from . import community_views
from . import community_reviewing_views

urlpatterns = [
    # Login
    path('', views.redirect_login, name='home-redirect'),
    path('login/', auth_views.LoginView.as_view(template_name='clara_app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/accounts/login/'), name='logout'),

    # Password reset links (ref: https://github.com/django/django/blob/master/django/contrib/auth/urls.py)
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Account
    path('register/', accounts_views.register, name='register'),
    path('profile/', accounts_views.profile, name='profile'),

    # Home
    path('home/', home_views.home, name='home'),
    path('home_page/', home_views.home_page, name='home_page'),
    path('clara_home_page/', home_views.clara_home_page, name='clara_home_page'),

    # Profile
    path('external_profile/<int:user_id>/', profile_views.external_profile, name='external_profile'),
    path('edit_profile/', profile_views.edit_profile, name='edit_profile'),

    # Config
    path('user_config/', user_config_views.user_config, name='user_config'),

    # Listing users and friends
    path('list_users/', users_and_friends_views.list_users, name='list_users'),
    path('friends/', users_and_friends_views.friends, name='friends'),

    # Update feed
    path('update_feed/', update_feed_views.update_feed, name='update_feed'),

    # Task updates
    path('view_task_updates/', task_update_views.view_task_updates, name='view_task_updates'),
    path('delete_old_task_updates/', task_update_views.delete_old_task_updates, name='delete_old_task_updates'),

    # Admin functions to change permissions
    path('admin_password_reset/', admin_permission_views.admin_password_reset, name='admin_password_reset'),
    path('admin_project_ownership/', admin_permission_views.admin_project_ownership, name='admin_project_ownership'),
    path('manage_user_permissions/', admin_permission_views.manage_user_permissions, name='manage_user_permissions'),

    # Credit
    path('add_credit/', credit_views.add_credit, name='add_credit'),
    path('transfer_credit/', credit_views.transfer_credit, name='transfer_credit'),
    path('confirm_transfer/', credit_views.confirm_transfer, name='confirm_transfer'),
    path('credit_balance/', credit_views.credit_balance, name='credit_balance'),

    # Deleting TTS data
    path('delete_tts_data/', delete_tts_views.delete_tts_data, name='delete_tts_data'),
    path('delete_tts_data_status/<str:report_id>/', delete_tts_views.delete_tts_data_status, name='delete_tts_data_status'),
    path('delete_tts_data_monitor/<str:language>/<str:report_id>/', delete_tts_views.delete_tts_data_monitor, name='delete_tts_data_monitor'),
    path('delete_tts_data_complete/<str:language>/<str:status>/', delete_tts_views.delete_tts_data_complete, name='delete_tts_data_complete'),

    # Registering and listing content
    path('register_content/', content_views.register_content, name='register_content'),
    path('content_success/', content_views.content_success, name='content_success'),
    path('content_list/', content_views.content_list, name='content_list'),
    path('public_content_list/', content_views.public_content_list, name='public_content_list'),
    path('content/<int:content_id>/', content_views.content_detail, name='content_detail'),
    path('public_content/<int:content_id>/', content_views.public_content_detail, name='public_content_detail'),
    path('language_statistics/', content_views.language_statistics, name='language_statistics'),

    # Managing language masters
    path('manage_language_masters/', language_masters_views.manage_language_masters, name='manage_language_masters'),
    path('remove_language_master/<int:pk>/', language_masters_views.remove_language_master, name='remove_language_master'),

    # Funding requests
    path('funding_request/', funding_requests_views.funding_request, name='funding_request'),
    path('review_funding_requests/', funding_requests_views.review_funding_requests, name='review_funding_requests'),
    path('confirm_funding_approvals/', funding_requests_views.confirm_funding_approvals, name='confirm_funding_approvals'),

    # Activity tracker
    path('activity/<int:activity_id>/activity_detail/', activity_tracker_views.activity_detail, name='activity_detail'),
    path('create_activity/', activity_tracker_views.create_activity, name='create_activity'),
    path('list_activities/', activity_tracker_views.list_activities, name='list_activities'),
    path('list_activities_text/', activity_tracker_views.list_activities_text, name='list_activities_text'),
    path('ai_activities_reply/', activity_tracker_views.ai_activities_reply, name='ai_activities_reply'),

    # Editing annotation prompt templates and examples
    path('edit_prompt/', annotation_prompts_views.edit_prompt, name='edit_prompt'),

    # Phonetic lexica
    path('edit_phonetic_lexicon/', phonetic_lexicon_views.edit_phonetic_lexicon, name='edit_phonetic_lexicon'),
    path('import_phonetic_lexicon_status/<str:language>/<str:report_id>/', phonetic_lexicon_views.import_phonetic_lexicon_status, name='import_phonetic_lexicon_status'),
    path('import_phonetic_lexicon_monitor/<str:language>/<str:report_id>/', phonetic_lexicon_views.import_phonetic_lexicon_monitor, name='import_phonetic_lexicon_monitor'),
    path('import_phonetic_lexicon_complete/<str:language>/<str:status>/', phonetic_lexicon_views.import_phonetic_lexicon_complete, name='import_phonetic_lexicon_complete'),

    # Simple C-LARA
    path('project/<int:project_id>/simple_clara/<str:last_operation_status>/', simple_clara_views.simple_clara, name='simple_clara'),
    path('project/<int:project_id>/simple_clara_status/<str:report_id>/', simple_clara_views.simple_clara_status, name='simple_clara_status'),
    path('project/<int:project_id>/simple_clara_monitor/<str:report_id>/', simple_clara_views.simple_clara_monitor, name='simple_clara_monitor'),
    path('project/<int:project_id>/simple_clara_review_v2_images_for_page/<int:page_number>/<str:from_view>/<str:status>/', simple_clara_views.simple_clara_review_v2_images_for_page,
         name='simple_clara_review_v2_images_for_page'),
    path('project/<int:project_id>/simple_clara_review_v2_images_for_element/<str:element_name>/<str:from_view>/<str:status>/', simple_clara_views.simple_clara_review_v2_images_for_element,
         name='simple_clara_review_v2_images_for_element'),
    path('project/<int:project_id>/simple_clara_review_v2_images_for_style/<str:from_view>/<str:status>/', simple_clara_views.simple_clara_review_v2_images_for_style,
         name='simple_clara_review_v2_images_for_style'),

    path('project/<int:project_id>/execute_simple_clara_image_requests_monitor/<str:report_id>/<int:page_number>/<str:from_view>/', simple_clara_views.execute_simple_clara_image_requests_monitor,
         name='execute_simple_clara_image_requests_monitor'),
    path('project/<int:project_id>/execute_simple_clara_image_requests_status/<str:report_id>/', simple_clara_views.execute_simple_clara_image_requests_status,
         name='execute_simple_clara_image_requests_status'),

    path('project/<int:project_id>/execute_simple_clara_element_requests_monitor/<str:report_id>/<str:element_name>/<str:from_view>/', simple_clara_views.execute_simple_clara_element_requests_monitor,
         name='execute_simple_clara_element_requests_monitor'),
    path('project/<int:project_id>/execute_simple_clara_element_requests_status/<str:report_id>/', simple_clara_views.execute_simple_clara_element_requests_status,
         name='execute_simple_clara_element_requests_status'),

    path('project/<int:project_id>/execute_simple_clara_style_requests_monitor/<str:report_id>/<str:from_view>/', simple_clara_views.execute_simple_clara_style_requests_monitor,
         name='execute_simple_clara_style_requests_monitor'),
    path('project/<int:project_id>/execute_simple_clara_style_requests_status/<str:report_id>/', simple_clara_views.execute_simple_clara_style_requests_status,
         name='execute_simple_clara_style_requests_status'),

    # Creating projects
    path('create_project/', create_project_views.create_project, name='create_project'),
    path('import_project/', create_project_views.import_project, name='import_project'),
    path('project/<int:project_id>/import_project_status/<str:report_id>/', create_project_views.import_project_status, name='import_project_status'),
    path('project/<int:project_id>/import_project_monitor/<str:report_id>/', create_project_views.import_project_monitor, name='import_project_monitor'),
    path('project/<int:project_id>/import_project_complete/<str:status>/', create_project_views.import_project_complete, name='import_project_complete'),
    path('project/<int:project_id>/clone_project/', create_project_views.clone_project, name='clone_project'),

    # Manipulating projects
    path('project_list/<str:clara_version>/', manipulate_project_views.project_list, name='project_list'),
    path('project/<int:project_id>/', manipulate_project_views.project_detail, name='project_detail'),
    path('project/<int:project_id>/manage_project_members/', manipulate_project_views.manage_project_members, name='manage_project_members'),
    path('project/<int:permission_id>/remove_project_member/', manipulate_project_views.remove_project_member, name='remove_project_member'),
    path('project/<int:project_id>/delete/', manipulate_project_views.delete_project, name='delete_project'),  
    path('project/<int:project_id>/history/', manipulate_project_views.project_history, name='project_history'),

    # Making export zipfiles
    path('project/<int:project_id>/make_export_zipfile/', export_zipfile_views.make_export_zipfile, name='make_export_zipfile'),
    path('project/<int:project_id>/make_export_zipfile_status/<str:report_id>/', export_zipfile_views.make_export_zipfile_status, name='make_export_zipfile_status'),
    path('project/<int:project_id>/make_export_zipfile_monitor/<str:report_id>/', export_zipfile_views.make_export_zipfile_monitor, name='make_export_zipfile_monitor'),
    path('project/<int:project_id>/make_export_zipfile_complete/<str:status>/', export_zipfile_views.make_export_zipfile_complete, name='make_export_zipfile_complete'), 

    # Annotation
    path('project/<int:project_id>/create_plain_text/', annotation_views.create_plain_text, name='create_plain_text'),
    path('project/<int:project_id>/create_title/', annotation_views.create_title, name='create_title'),
    path('project/<int:project_id>/create_segmented_title/', annotation_views.create_segmented_title, name='create_segmented_title'),
    path('project/<int:project_id>/create_summary/', annotation_views.create_summary, name='create_summary'),
    path('project/<int:project_id>/create_cefr_level/', annotation_views.create_cefr_level, name='create_cefr_level'),
    path('project/<int:project_id>/create_segmented_text/', annotation_views.create_segmented_text, name='create_segmented_text'),
    path('project/<int:project_id>/create_translated_text/', annotation_views.create_translated_text, name='create_translated_text'),
    path('project/<int:project_id>/create_phonetic_text/', annotation_views.create_phonetic_text, name='create_phonetic_text'),
    path('project/<int:project_id>/create_glossed_text/', annotation_views.create_glossed_text, name='create_glossed_text'),
    path('project/<int:project_id>/create_glossed_text_from_lemma/', annotation_views.create_glossed_text_from_lemma, name='create_glossed_text_from_lemma'),
    path('project/<int:project_id>/create_lemma_tagged_text/', annotation_views.create_lemma_tagged_text, name='create_lemma_tagged_text'),
    path('project/<int:project_id>/create_mwe_tagged_text/', annotation_views.create_mwe_tagged_text, name='create_mwe_tagged_text'),
    path('project/<int:project_id>/create_pinyin_tagged_text/', annotation_views.create_pinyin_tagged_text, name='create_pinyin_tagged_text'),
    path('project/<int:project_id>/create_lemma_and_gloss_tagged_text/', annotation_views.create_lemma_and_gloss_tagged_text, name='create_lemma_and_gloss_tagged_text'),
    path('project/<int:project_id>/generate_text_status/<str:report_id>/', annotation_views.generate_text_status, name='generate_text_status'),
    path('project/<int:project_id>/generate_text_monitor/<str:version>/<str:report_id>/', annotation_views.generate_text_monitor, name='generate_text_monitor'),
    path('project/<int:project_id>/generate_text_complete/<str:version>/<str:status>/', annotation_views.generate_text_complete, name='generate_text_complete'),
    path('project/<int:project_id>/edit_acknowledgements/', annotation_views.edit_acknowledgements, name='edit_acknowledgements'),
    path('project/<int:project_id>/set_format_preferences/', annotation_views.set_format_preferences, name='set_format_preferences'),

    # Managing human-recorded audio
    path('project/<int:project_id>/audio_metadata/', human_audio_views.get_audio_metadata_view, name='get_audio_metadata'),
    path('project/<int:project_id>/human_audio_processing/', human_audio_views.human_audio_processing, name='human_audio_processing'),
    path('project/<int:project_id>/human_audio_processing_phonetic/', human_audio_views.human_audio_processing_phonetic, name='human_audio_processing_phonetic'),
    path('project/<int:project_id>/process_ldt_zipfile_status/<str:report_id>/', human_audio_views.process_ldt_zipfile_status, name='process_ldt_zipfile_status'),
    path('project/<int:project_id>/process_ldt_zipfile_monitor/<str:report_id>/', human_audio_views.process_ldt_zipfile_monitor, name='process_ldt_zipfile_monitor'),
    path('project/<int:project_id>/process_ldt_zipfile_complete/<str:status>/', human_audio_views.process_ldt_zipfile_complete, name='process_ldt_zipfile_complete'),
    path('project/<int:project_id>/generate_audio_metadata/<str:metadata_type>/<str:human_voice_id>/', human_audio_views.generate_audio_metadata, name='generate_audio_metadata'),
    path('project/<int:project_id>/generate_audio_metadata_phonetic/<str:metadata_type>/<str:human_voice_id>/', human_audio_views.generate_audio_metadata_phonetic, name='generate_audio_metadata_phonetic'),
    path('project/<int:project_id>/process_manual_alignment_status/<str:report_id>/', human_audio_views.process_manual_alignment_status, name='process_manual_alignment_status'),
    path('project/<int:project_id>/process_manual_alignment_monitor/<str:report_id>/', human_audio_views.process_manual_alignment_monitor, name='process_manual_alignment_monitor'),
    path('project/<int:project_id>/process_manual_alignment_complete/<str:status>/', human_audio_views.process_manual_alignment_complete, name='process_manual_alignment_complete'),
    path('project/<int:project_id>/generate_annotated_segmented_file/', human_audio_views.generate_annotated_segmented_file, name='generate_annotated_segmented_file'),

    # Edit images, v1
    path('project/<int:project_id>/edit_images/<str:dall_e_3_image_status>', images_v1_views.edit_images, name='edit_images'),
    path('project/<int:project_id>/create_dall_e_3_image_status/<str:report_id>/', images_v1_views.create_dall_e_3_image_status, name='create_dall_e_3_image_status'),
    path('project/<int:project_id>/create_dall_e_3_image_monitor/<str:report_id>/', images_v1_views.create_dall_e_3_image_monitor, name='create_dall_e_3_image_monitor'),
    path('project/<int:project_id>/access_archived_images/<str:image_name>', images_v1_views.access_archived_images, name='access_archived_images'),
    path('project/<int:project_id>/restore_image/<str:archived_image_id>', images_v1_views.restore_image, name='restore_image'),
    path('project/<int:project_id>/delete_archive_image/<str:archived_image_id>', images_v1_views.delete_archive_image, name='delete_archive_image'),

    # Edit images, v2
    path('project/<int:project_id>/edit_images_v2/<str:status>', images_v2_views.edit_images_v2, name='edit_images_v2'),
    path('project/<int:project_id>/coherent_images_v2_status/<str:report_id>/', images_v2_views.coherent_images_v2_status, name='coherent_images_v2_status'),
    path('project/<int:project_id>/coherent_images_v2_monitor/<str:report_id>/', images_v2_views.coherent_images_v2_monitor, name='coherent_images_v2_monitor'),

    # Saving page texts in pages and images view
    path('project/<int:project_id>/save_page_texts_multiple_status/<str:report_id>/', save_page_texts_multiple_views.save_page_texts_multiple_status, name='save_page_texts_multiple_status'),
    path('project/<int:project_id>/save_page_texts_multiple_monitor/<str:report_id>/', save_page_texts_multiple_views.save_page_texts_multiple_monitor, name='save_page_texts_multiple_monitor'), 

    # Creating and managing communities
    path('create_community/', community_views.create_community, name='create_community'),
    path('delete_community_menu/', community_views.delete_community_menu, name='delete_community_menu'),
    path('community_home/<int:community_id>/', community_views.community_home, name='community_home'),
    path('assign_coordinator_to_community/', community_views.assign_coordinator_to_community, name='assign_coordinator_to_community'),
    path('assign_member_to_community/', community_views.assign_member_to_community, name='assign_member_to_community'),
    path('project/<int:project_id>/project_community/', community_views.project_community, name='project_community'),

    # Community reviewing of images
    path('project/<int:project_id>/community_review_images/', community_reviewing_views.community_review_images, name='community_review_images'),
    path('project/<int:project_id>/community_organiser_review_images/', community_reviewing_views.community_organiser_review_images, name='community_organiser_review_images'),
    path('project/<int:project_id>/community_review_images_external/', community_reviewing_views.community_review_images_external, name='community_review_images_external'),
    path('project/<int:project_id>/community_review_images_for_page/<int:page_number>/<str:cm_or_co>/<str:status>/', community_reviewing_views.community_review_images_for_page,
         name='community_review_images_for_page'),
    path('project/<int:project_id>/execute_community_requests_for_page_monitor/<str:report_id>/<int:page_number>/', community_reviewing_views.execute_community_requests_for_page_monitor,
         name='execute_community_requests_for_page_monitor'),
    path('project/<int:project_id>/execute_community_requests_for_page_status/<str:report_id>/', community_reviewing_views.execute_community_requests_for_page_status,
         name='execute_community_requests_for_page_status'),

    # Image questionnaires
    path('image_questionnaire_project_list/', views.image_questionnaire_project_list, name='image_questionnaire_project_list'),
    path('project/<int:project_id>/image_questionnaire_start', views.image_questionnaire_start, name='image_questionnaire_start'),
    path('project/<int:project_id>/image_questionnaire_item/<int:index>', views.image_questionnaire_item, name='image_questionnaire_item'),
    path('project/<int:project_id>/image_questionnaire_summary', views.image_questionnaire_summary, name='image_questionnaire_summary'),
    path('image_questionnaire_all_projects_summary/', views.image_questionnaire_all_projects_summary, name='image_questionnaire_all_projects_summary'),

    # Compare versions of annotated text
    path('projects/<int:project_id>/compare_versions/', views.compare_versions, name='compare_versions'),
    path('projects/<int:project_id>/metadata/<str:version>/', views.get_metadata_for_version, name='get_metadata_for_version'),
    
    # Rendering text
    path('project/<int:project_id>/render_text_start_normal/', views.render_text_start_normal, name='render_text_start_normal'),
    path('project/<int:project_id>/render_text_start_phonetic/', views.render_text_start_phonetic, name='render_text_start_phonetic'),
    path('project/<int:project_id>/render_text_status/<str:report_id>/', views.render_text_status, name='render_text_status'),
    path('project/<int:project_id>/render_text_monitor/<str:phonetic_or_normal>/<str:report_id>/', views.render_text_monitor, name='render_text_monitor'),
    path('project/<int:project_id>/render_text_complete/<str:phonetic_or_normal>/<str:status>/', views.render_text_complete, name='render_text_complete'),

    # Registering content
    path('project/<int:project_id>/offer_to_register_content_normal/', views.offer_to_register_content_normal, name='offer_to_register_content_normal'),
    path('project/<int:project_id>/offer_to_register_content_phonetic/', views.offer_to_register_content_phonetic, name='offer_to_register_content_phonetic'),
    path('project/<int:project_id>/register_project_content/<str:phonetic_or_normal>/', views.register_project_content, name='register_project_content'),

    # Satisfaction questionnaire
    path('project/<int:project_id>/satisfaction_questionnaire/', views.satisfaction_questionnaire, name='satisfaction_questionnaire'),
    path('project/<int:project_id>/show_questionnaire/<int:user_id>/', views.show_questionnaire, name='show_questionnaire'),
    path('project/aggregated_questionnaire_results/', views.aggregated_questionnaire_results, name='aggregated_questionnaire_results'),
    path('project/manage_questionnaires/', views.manage_questionnaires, name='manage_questionnaires'),

    # Reading history
    path('reading_history/<str:l2_language>/<str:status>/', views.reading_history, name='reading_history'),
    path('update_reading_history_status/<str:l2_language>/<str:report_id>/', views.update_reading_history_status, name='update_reading_history_status'),
    path('update_reading_history_monitor/<str:l2_language>/<str:report_id>/', views.update_reading_history_monitor, name='update_reading_history_monitor'),

    # Serving content
    path('rendered_texts/<int:project_id>/<str:phonetic_or_normal>/static/<path:filename>', views.serve_rendered_text_static, name='serve_rendered_text'),
    path('rendered_texts/<int:project_id>/<str:phonetic_or_normal>/multimedia/<path:filename>', views.serve_rendered_text_multimedia, name='serve_rendered_text'),
    path('rendered_texts/<int:project_id>/<str:phonetic_or_normal>/<path:filename>', views.serve_rendered_text, name='serve_rendered_text'),

    path('serve_coherent_images_v2_overview/<int:project_id>/', views.serve_coherent_images_v2_overview, name='serve_coherent_images_v2_overview'),
    path('serve_zipfile/<int:project_id>/', views.serve_zipfile, name='serve_zipfile'),
    path('serve_export_zipfile/<int:project_id>/', views.serve_export_zipfile, name='serve_export_zipfile'),

    path('projects/serve_project_image/<str:project_id>/<path:base_filename>', views.serve_project_image, name='serve_project_image'),
    path(
        'accounts/projects/serve_coherent_images_v2_file/<int:project_id>/<path:relative_path>/',
        views.serve_coherent_images_v2_file,
        name='serve_coherent_images_v2_file'
    ),
    path('serve_audio_file/<str:engine_id>/<str:l2>/<str:voice_id>/<str:base_filename>', views.serve_audio_file, name='serve_audio_file'),

##    path('manual_audio_alignment_integration_endpoint1/<int:project_id>/', views.manual_audio_alignment_integration_endpoint1, name='manual_audio_alignment_integration_endpoint1'),
##    path('manual_audio_alignment_integration_endpoint2/', views.manual_audio_alignment_integration_endpoint2, name='manual_audio_alignment_integration_endpoint2'),

]

