from .models import DartsGroup


DEFAULT_DARTS_GROUP = "Család"


def get_current_darts_group(user):
    """Return the user's darts group, creating/joining the shared family group if needed."""
    group = user.darts_groups.order_by("id").first()
    if group:
        return group

    group, _created = DartsGroup.objects.get_or_create(name=DEFAULT_DARTS_GROUP)
    group.members.add(user)
    return group
