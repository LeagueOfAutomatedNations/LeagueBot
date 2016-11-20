def describe_duration(battle_data):
    if 'duration' in battle_data:
        if battle_data['battle_still_ongoing']:
            return "{0:03d}+".format(battle_data['duration'])
        else:
            return "{0:03d}".format(battle_data['duration'])
    else:
        return "???"


def describe_defender(battle_data):
    if 'owner' in battle_data:
        return ", {} defending".format(battle_data['owner'])
    else:
        return ""


def describe_creeps(battle_data):
    # Sort by a tuple of (not the owner, username) so that the owner of a room always comes first.
    items_list = sorted(battle_data['player_creep_counts'].items(),
                        key=lambda t: (t[0] != battle_data.get('owner'), t[0]))
    return " vs ".join("{}'s {}".format(name, describe_player_creep_list(parts)) for name, parts in items_list)


def describe_player_creep_list(creeps):
    creeps = sorted(creeps.items(), key=lambda t: t[0])
    if len(creeps) >= 2:
        last_role, last_count = creeps[-1]
        return "{} and {}".format(
            ", ".join(describe_creep(role, count) for role, count in creeps[:-1]),
            describe_creep(last_role, last_count)
        )
    else:
        return ", ".join(describe_creep(role, count) for role, count in creeps)


def describe_creep(role, count):
    if count > 1:
        return "{} {}s".format(count, role)
    else:
        return "{} {}".format(count, role)
