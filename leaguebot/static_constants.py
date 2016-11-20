from leaguebot import app

####
# Redis keys
####

DATABASE_PREFIX = app.config.get('REDIS_PREFIX', 'leaguebot:')

_VERSION = "0.2"
PROCESSING_QUEUE = DATABASE_PREFIX + _VERSION + ":processing_queue"
PROCESSING_QUEUE_SET = DATABASE_PREFIX + _VERSION + ":processing_set"

REPORTING_QUEUE = DATABASE_PREFIX + _VERSION + ":reporting_queue"

USERNAME_CACHE_KEY = DATABASE_PREFIX + "cache:username:{}"
USERNAME_CACHE_EXPIRE = 60 * 60 * 5

ALLIANCE_CACHE_KEY = DATABASE_PREFIX + "cache:alliance:{}"
ALLIANCE_CACHE_EXPIRE = 60 * 60 * 5

ALLIANCES_FETCHED_KEY = DATABASE_PREFIX + "fetched-alliance-cache"
ALLIANCES_FETCHED_EXPIRE = 60 * 60 * 4

BATTLE_DATA_KEY = DATABASE_PREFIX + "ongoing-data:{}"
# if it's still in here for 3 days, something has gone wrong and we can just get rid of it.
BATTLE_DATA_EXPIRE = 60 * 60 * 24 * 3

ROOM_LAST_BATTLE_END_TICK_KEY = DATABASE_PREFIX + "last-finished-battle:{}"
ROOM_LAST_BATTLE_END_TICK_EXPIRE = 60 * 60 * 24 * 10

LAST_CHECKED_TICK_KEY = DATABASE_PREFIX + "last-checked-tick"
LAST_CHECKED_TICK_EXPIRE = 60 * 60

####
# Predefined settings (should these be configurable?)
####

"""
NOTE: This max ticks is max history ticks successfully retrieved after starting.
"""
KEEP_IN_QUEUE_FOR_MAX_TICKS = 120

"""
This is the hard deadline where no more history collection will be attempted (if the current tick is this many ticks
after the last known hostilities (or the first hostilities if no history has been found), give up.)
"""
KEEP_IN_QUEUE_FOR_MAX_TICKS_UNSUCCESSFUL = 2000

CHECK_BATTLES_ENDPOINT_EVERY_SECONDS = 15 * 60

####
# Creep types used in battle info
####

ranged_attacker = "ranged attacker"
melee_attacker = "melee attacker"
healer = 'healer'
dismantling_attacker = 'dismantler'
general_attacker = 'general attacker'
tough_attacker = 'tough guy'
work_and_carry_attacker = 'multi-purpose attacker'
civilian = 'civilian'
scout = 'scout'


####
# Errors defined. TODO: find somewhere better to put this
####

class ScreepsError(Exception):
    def __init__(self, data):
        self.message = "Screeps API Error: {}".format(data)

    def __str__(self):
        return self.message
