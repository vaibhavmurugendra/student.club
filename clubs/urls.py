from django.urls import path
from . import views

urlpatterns = [
    path('clubs/search/', views.club_search, name='club_search'),
    path('', views.home, name='home'),
    path('clubs/', views.club_list, name='club_list'),
    path('clubs/<int:club_id>/', views.club_detail, name='club_detail'),
    path('clubs/create/', views.create_club, name='create_club'),
    path('clubs/<int:club_id>/edit/', views.edit_club, name='edit_club'),
    path('clubs/<int:club_id>/join/', views.join_club, name='join_club'),
    path('clubs/<int:club_id>/polls/create/', views.create_poll, name='create_poll'),
    path('polls/<int:poll_id>/vote/', views.vote_poll, name='vote_poll'),
    path('clubs/<int:club_id>/proposals/', views.proposal_list, name='proposal_list'),
    path('clubs/<int:club_id>/proposals/create/', views.create_proposal, name='create_proposal'),
    path('proposals/<int:proposal_id>/vote/', views.vote_proposal, name='vote_proposal'),
    path('proposals/<int:proposal_id>/unvote/', views.unvote_proposal, name='unvote_proposal'),
    path('proposals/<int:proposal_id>/delete/', views.delete_proposal, name='delete_proposal'),
    path('register/', views.register, name='register'),
    path('clubs/<int:club_id>/manage-roles/', views.manage_roles, name='manage_roles'),
    path('clubs/<int:club_id>/update-member-role/<int:member_id>/', views.update_member_role, name='update_member_role'),
    path('clubs/<int:club_id>/remove-member/<int:member_id>/', views.remove_member, name='remove_member'),
]