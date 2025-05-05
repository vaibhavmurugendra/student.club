from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Club, Member, Poll, PollOption, Vote, Proposal, ProposalVote
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden

def home(request):
    if request.user.is_authenticated:
        # Get clubs where the user is a member, ordered by name and creation date
        clubs = Club.objects.filter(member__user=request.user).order_by('name', '-created_at')
    else:
        # For non-authenticated users, show empty queryset
        clubs = Club.objects.none()
    
    return render(request, 'home.html', {'clubs': clubs})

def club_list(request):
    search_query = request.GET.get('q', '').strip()
    clubs = Club.objects.all()
    
    if search_query:
        try:
            # Import required libraries
            from fuzzywuzzy import process, fuzz
            from django.db.models import Q
            
            # Get all clubs for fuzzy matching
            all_clubs = list(clubs)
            matched_clubs = set()  # Using set to avoid duplicates
            
            # Fuzzy match on club names with token sort ratio for better partial matches
            club_names = [(club.id, club.name) for club in all_clubs]
            name_matches = process.extract(
                search_query,
                [name for _, name in club_names],
                scorer=fuzz.token_sort_ratio,
                limit=15
            )
            
            # Add clubs with name matches that score above 55
            for name, score in name_matches:
                if score >= 55:
                    for club_id, club_name in club_names:
                        if club_name == name:
                            matched_clubs.add(next(club for club in all_clubs if club.id == club_id))
            
            # Fuzzy match on descriptions with token set ratio for better content matching
            club_descriptions = [(club.id, club.description or '') for club in all_clubs]
            desc_matches = process.extract(
                search_query,
                [desc for _, desc in club_descriptions],
                scorer=fuzz.token_set_ratio,
                limit=15
            )
            
            # Add clubs with description matches that score above 45
            for desc, score in desc_matches:
                if score >= 45:
                    for club_id, club_desc in club_descriptions:
                        if club_desc == desc:
                            matched_clubs.add(next(club for club in all_clubs if club.id == club_id))
            
            # If no fuzzy matches or search query is very short, fall back to contains search
            if not matched_clubs or len(search_query) <= 2:
                clubs = clubs.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                ).distinct()
            else:
                clubs = sorted(list(matched_clubs), key=lambda x: x.name.lower())
        except Exception as e:
            # Log the error and fallback to basic search
            print(f'Search error: {str(e)}')
            clubs = clubs.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
    
    # Sort results
    clubs = sorted(clubs, key=lambda x: x.name.lower()) if isinstance(clubs, list) else clubs.order_by('name')
    
    # Return JSON response for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        club_data = [{
            'id': club.id,
            'name': club.name,
            'description': club.description,
            'logo': club.logo.url if club.logo else None,
            'created_at': club.created_at.isoformat()
        } for club in clubs]
        return JsonResponse({'clubs': club_data})
    
    return render(request, 'clubs/club_list.html', {'clubs': clubs, 'search_query': search_query})

@login_required
def club_detail(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    is_member = Member.objects.filter(club=club, user=request.user).exists()
    user_is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    active_polls = Poll.objects.filter(club=club, end_date__gt=timezone.now())
    return render(request, 'clubs/club_detail.html', {
        'club': club,
        'is_member': is_member,
        'user_is_admin': user_is_admin,
        'active_polls': active_polls
    })

@login_required
def edit_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    # Check if user is an admin of the club
    if not Member.objects.filter(club=club, user=request.user, role='ADMIN').exists():
        return HttpResponseForbidden("You don't have permission to edit this club.")
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        logo = request.FILES.get('logo')
        
        club.name = name
        club.description = description
        if logo:
            club.logo = logo
        club.save()
        
        messages.success(request, 'Club updated successfully!')
        return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/edit_club.html', {'club': club})

@login_required
def create_club(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        logo = request.FILES.get('logo')
        
        club = Club.objects.create(
            name=name,
            description=description,
            logo=logo,
            creator=request.user
        )
        
        # Make the creator an admin member
        Member.objects.create(user=request.user, club=club, role='ADMIN')
        
        messages.success(request, 'Club created successfully!')
        return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/create_club.html')

@login_required
def join_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    if not Member.objects.filter(club=club, user=request.user).exists():
        Member.objects.create(user=request.user, club=club)
        messages.success(request, f'You have joined {club.name}!')
    return redirect('club_detail', club_id=club.id)

@login_required
def create_poll(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    member = get_object_or_404(Member, club=club, user=request.user)
    
    if member.role != 'ADMIN':
        messages.error(request, 'Only club admins can create polls.')
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        end_date = request.POST.get('end_date')
        options = request.POST.getlist('options')
        
        poll = Poll.objects.create(
            club=club,
            title=title,
            description=description,
            end_date=end_date,
            created_by=request.user
        )
        
        for option_text in options:
            PollOption.objects.create(poll=poll, text=option_text)
        
        messages.success(request, 'Poll created successfully!')
        return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/create_poll.html', {'club': club})

@login_required
def vote_poll(request, poll_id):
    poll = get_object_or_404(Poll, id=poll_id)
    
    if not poll.is_active():
        messages.error(request, 'This poll has ended.')
        return redirect('club_detail', club_id=poll.club.id)
    
    if request.method == 'POST':
        option_id = request.POST.get('option')
        option = get_object_or_404(PollOption, id=option_id, poll=poll)
        
        # Check if user has already voted
        if not Vote.objects.filter(poll=poll, user=request.user).exists():
            Vote.objects.create(poll=poll, option=option, user=request.user)
            messages.success(request, 'Your vote has been recorded!')
        else:
            messages.error(request, 'You have already voted in this poll.')
    
    return redirect('club_detail', club_id=poll.club.id)


@login_required
def manage_roles(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    user_is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    
    if not user_is_admin:
        messages.error(request, 'Only club admins can manage roles.')
        return redirect('club_detail', club_id=club.id)
    
    members = Member.objects.filter(club=club).select_related('user')
    role_choices = Member.ROLE_CHOICES
    
    return render(request, 'clubs/manage_roles.html', {
        'club': club,
        'members': members,
        'role_choices': role_choices
    })

@login_required
def remove_member(request, club_id, member_id):
    club = get_object_or_404(Club, id=club_id)
    member = get_object_or_404(Member, id=member_id, club=club)
    user_is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    
    if not user_is_admin:
        messages.error(request, 'Only club admins can remove members.')
        return redirect('club_detail', club_id=club.id)
    
    if member.role == 'ADMIN' and member.user != request.user:
        messages.error(request, 'You cannot remove other admins from the club.')
        return redirect('manage_roles', club_id=club.id)
    
    if request.method == 'POST':
        # Delete all votes by this member in this club's polls
        Vote.objects.filter(poll__club=club, user=member.user).delete()
        
        # Delete all proposal votes by this member in this club
        ProposalVote.objects.filter(proposal__club=club, user=member.user).delete()
        
        # Delete the member's proposals in this club
        Proposal.objects.filter(club=club, created_by=member.user).delete()
        
        # Finally remove the member
        member.delete()
        messages.success(request, f'{member.user.username} has been removed from the club.')
    
    return redirect('manage_roles', club_id=club.id)

@login_required
def update_member_role(request, club_id, member_id):
    club = get_object_or_404(Club, id=club_id)
    member = get_object_or_404(Member, id=member_id, club=club)
    user_is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    
    if not user_is_admin:
        messages.error(request, 'Only club admins can update roles.')
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in dict(Member.ROLE_CHOICES):
            member.role = new_role
            member.save()
            messages.success(request, f'Role updated successfully for {member.user.username}.')
        else:
            messages.error(request, 'Invalid role selected.')
    
    return redirect('manage_roles', club_id=club.id)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
    return render(request, 'registration/register.html')

@login_required
def proposal_list(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    is_member = Member.objects.filter(club=club, user=request.user).exists()
    is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    proposals = Proposal.objects.filter(club=club).order_by('-created_at')
    
    # Check if the user has voted on each proposal
    user_voted = {}
    if is_member:
        for proposal in proposals:
            user_voted[proposal.id] = ProposalVote.objects.filter(proposal=proposal, user=request.user).exists()
    
    return render(request, 'clubs/proposal_list.html', {
        'club': club,
        'proposals': proposals,
        'is_member': is_member,
        'is_admin': is_admin,
        'user_voted': user_voted
    })

@login_required
def create_proposal(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    is_member = Member.objects.filter(club=club, user=request.user).exists()
    
    if not is_member:
        messages.error(request, 'You must be a member to create proposals.')
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        
        proposal = Proposal.objects.create(
            club=club,
            title=title,
            description=description,
            created_by=request.user
        )
        
        messages.success(request, 'Proposal created successfully!')
        return redirect('proposal_list', club_id=club.id)
    else:
        # For GET requests, render the form template
        return render(request, 'clubs/create_proposal.html', {
            'club': club
        })

@login_required
def delete_proposal(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    club = proposal.club
    
    # Check if user is the creator of the proposal or an admin of the club
    is_creator = proposal.created_by == request.user
    is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    
    if not (is_creator or is_admin):
        messages.error(request, 'You do not have permission to delete this proposal.')
        return redirect('proposal_list', club_id=club.id)
    
    if request.method == 'POST':
        # Delete all votes for this proposal first
        ProposalVote.objects.filter(proposal=proposal).delete()
        # Then delete the proposal
        proposal.delete()
        messages.success(request, 'Proposal deleted successfully!')
    
    return redirect('proposal_list', club_id=club.id)

@login_required
def vote_proposal(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    club = proposal.club
    is_member = Member.objects.filter(club=club, user=request.user).exists()
    
    if not is_member:
        messages.error(request, 'You must be a member to vote on proposals.')
        return redirect('club_detail', club_id=club.id)
    
    # Check if user has already voted
    if not ProposalVote.objects.filter(proposal=proposal, user=request.user).exists():
        ProposalVote.objects.create(proposal=proposal, user=request.user)
        messages.success(request, 'Your vote has been recorded!')
    else:
        messages.info(request, 'You have already voted on this proposal.')
    
    return redirect('proposal_list', club_id=club.id)

@login_required
def delete_proposal(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    club = proposal.club
    
    # Check if user is the creator of the proposal or an admin of the club
    is_creator = proposal.created_by == request.user
    is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    
    if not (is_creator or is_admin):
        messages.error(request, 'You do not have permission to delete this proposal.')
        return redirect('proposal_list', club_id=club.id)
    
    if request.method == 'POST':
        # Delete all votes for this proposal first
        ProposalVote.objects.filter(proposal=proposal).delete()
        # Then delete the proposal
        proposal.delete()
        messages.success(request, 'Proposal deleted successfully!')
    
    return redirect('proposal_list', club_id=club.id)

@login_required
def unvote_proposal(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    club = proposal.club
    is_member = Member.objects.filter(club=club, user=request.user).exists()
    
    if not is_member:
        messages.error(request, 'You must be a member to unvote on proposals.')
        return redirect('club_detail', club_id=club.id)
    
    # Check if user has already voted and remove the vote
    vote = ProposalVote.objects.filter(proposal=proposal, user=request.user).first()
    if vote:
        vote.delete()
        messages.success(request, 'Your vote has been removed!')
    else:
        messages.info(request, 'You have not voted on this proposal.')
    
    return redirect('proposal_list', club_id=club.id)

@login_required
def delete_proposal(request, proposal_id):
    proposal = get_object_or_404(Proposal, id=proposal_id)
    club = proposal.club
    
    # Check if user is the creator of the proposal or an admin of the club
    is_creator = proposal.created_by == request.user
    is_admin = Member.objects.filter(club=club, user=request.user, role='ADMIN').exists()
    
    if not (is_creator or is_admin):
        messages.error(request, 'You do not have permission to delete this proposal.')
        return redirect('proposal_list', club_id=club.id)
    
    if request.method == 'POST':
        # Delete all votes for this proposal first
        ProposalVote.objects.filter(proposal=proposal).delete()
        # Then delete the proposal
        proposal.delete()
        messages.success(request, 'Proposal deleted successfully!')
    
    return redirect('proposal_list', club_id=club.id)

def club_search(request):
    search_query = request.GET.get('q', '').strip()
    clubs = Club.objects.all()
    
    if search_query:
        try:
            # Import required libraries
            from fuzzywuzzy import process, fuzz
            from django.db.models import Q
            
            # Get all clubs for fuzzy matching
            all_clubs = list(clubs)
            matched_clubs = set()  # Using set to avoid duplicates
            
            # Fuzzy match on club names with token sort ratio for better partial matches
            club_names = [(club.id, club.name) for club in all_clubs]
            name_matches = process.extract(
                search_query,
                [name for _, name in club_names],
                scorer=fuzz.token_sort_ratio,
                limit=15
            )
            
            # Add clubs with name matches that score above 55
            for name, score in name_matches:
                if score >= 55:
                    for club_id, club_name in club_names:
                        if club_name == name:
                            matched_clubs.add(next(club for club in all_clubs if club.id == club_id))
            
            # Fuzzy match on descriptions with token set ratio for better content matching
            club_descriptions = [(club.id, club.description or '') for club in all_clubs]
            desc_matches = process.extract(
                search_query,
                [desc for _, desc in club_descriptions],
                scorer=fuzz.token_set_ratio,
                limit=15
            )
            
            # Add clubs with description matches that score above 45
            for desc, score in desc_matches:
                if score >= 45:
                    for club_id, club_desc in club_descriptions:
                        if club_desc == desc:
                            matched_clubs.add(next(club for club in all_clubs if club.id == club_id))
            
            # If no fuzzy matches or search query is very short, fall back to contains search
            if not matched_clubs or len(search_query) <= 2:
                clubs = clubs.filter(
                    Q(name__icontains=search_query) |
                    Q(description__icontains=search_query)
                ).distinct()
            else:
                clubs = sorted(list(matched_clubs), key=lambda x: x.name.lower())
        except Exception as e:
            # Log the error and fallback to basic search
            print(f'Search error: {str(e)}')
            clubs = clubs.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
    
    # Sort results
    clubs = sorted(clubs, key=lambda x: x.name.lower()) if isinstance(clubs, list) else clubs.order_by('name')
    
    # Return JSON response
    from django.http import JsonResponse
    club_data = [{
        'id': club.id,
        'name': club.name,
        'description': club.description,
        'logo': club.logo.url if club.logo else None,
        'created_at': club.created_at.isoformat()
    } for club in clubs]
    return JsonResponse({'clubs': club_data})
