
from django.shortcuts import get_object_or_404
from .models import CLARAProject, Community

def assign_project_to_community(project_id, community_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    community = get_object_or_404(Community, pk=community_id)
    if project.l2 != community.language:
        raise ValidationError("Project L2 does not match community language")
    project.community = community
    project.save()

def user_in_project_community(user, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    if not project.community:
        return False
    # check if user belongs to that community
    membership_exists = CommunityMembership.objects.filter(
        community=project.community, user=user
    ).exists()
    return membership_exists

def user_is_coordinator_of_project_community(user, project_id):
    project = get_object_or_404(CLARAProject, pk=project_id)
    if not project.community:
        return False
    membership = CommunityMembership.objects.filter(
        community=project.community, user=user
    ).first()
    return membership and membership.role == 'COORDINATOR'
