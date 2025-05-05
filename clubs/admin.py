from django.contrib import admin
from .models import Club, Member, Poll, PollOption, Vote

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created_at')
    search_fields = ('name', 'description')

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'club', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'club__name')

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('title', 'club', 'created_by', 'created_at', 'end_date', 'is_active')
    list_filter = ('created_at', 'end_date')
    search_fields = ('title', 'description')

@admin.register(PollOption)
class PollOptionAdmin(admin.ModelAdmin):
    list_display = ('text', 'poll')
    search_fields = ('text', 'poll__title')

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'poll', 'option', 'voted_at')
    list_filter = ('voted_at',)
    search_fields = ('user__username', 'poll__title')
