import os
import os.path
import sys
from hypixelpy import hypixel
import time
from typing import List

def sleep_for_rate_limiting(seconds) -> None:
    if seconds > 15:
        print("Sleeping " + str(round(seconds, 2)) + " seconds for rate limiting...")
    time.sleep(seconds)

def fkdr_division(final_kills: int, final_deaths: int) -> float:
    return final_kills / final_deaths if final_deaths else float(final_kills)

def how_long_to_sleep(num_api_calls_made: int, time_passed: float) -> float:
    # Hypixel API default rate limit is 120 calls per min.
    if num_api_calls_made < 100 or num_api_calls_made / time_passed < 1.8:
        return 0
    goal_time_passed = num_api_calls_made / 1.8
    return goal_time_passed - time_passed + 5

def set_api_keys() -> None:
    API_KEYS = []
    with open('api-key.txt') as file:
        for line in file:
            API_KEYS.append(line.rstrip())
    hypixel.setKeys(API_KEYS)

def list_subtract(main_list: List, subtract_list: List) -> List:
    return [x for x in main_list if x not in subtract_list]

def get_ign_uuid_pairs() -> dict:
    if not os.path.isfile('uuids.txt'):
        return {}
    ign_uuid_pairs = {} # key ign, value uuid
    with open('uuids.txt') as file:
        for line in file:
            words = line.rstrip().split()
            ign_uuid_pairs[words[0].lower()] = words[1]
    return ign_uuid_pairs

def create_player_object(playerName) -> hypixel.Player:
    # Use this function if you're using the player's ign, rather than the uuid.
    ign_uuid_pairs = get_ign_uuid_pairs() # dict where the key is a player's ign, value is uuid
    return hypixel.Player(ign_uuid_pairs.get(playerName, playerName))

def calculate_fkdr(player: hypixel.Player) -> float:
    if ('final_kills_bedwars' not in player.JSON['stats']['Bedwars'] or
        'final_deaths_bedwars' not in player.JSON['stats']['Bedwars']):
        return 0.0
    return fkdr_division(player.JSON['stats']['Bedwars']['final_kills_bedwars'], 
                         player.JSON['stats']['Bedwars']['final_deaths_bedwars'])

def iterate_over_friends(playerFriendsUUIDS, just_online_friends: bool) -> List[dict]:
    friends_data = []
    time_started = time.time()
    for i in range(len(playerFriendsUUIDS)):
        if i % 10 == 0:
            print("Processed " + str(i))
        sleep_for_rate_limiting(how_long_to_sleep(i*2, time.time() - time_started))
        friend = hypixel.Player(playerFriendsUUIDS[i])
        if just_online_friends and not friend.isOnline():
            continue
        data = {'name': friend.getName(), 'FKDR': calculate_fkdr(friend), 'UUID': friend.getUUID()}
        print(str(data))
        friends_data.append(data)
    return sorted(friends_data, key=lambda d: d['FKDR'], reverse=True)

def remove_friends_who_logged_off(friends: List[dict]) -> List[dict]:
    updated_friends = []
    for i in range(len(friends)):
        if i % 5 == 0 and i > 0:
            sleep_for_rate_limiting(5)
        if hypixel.Player(friends[i]['UUID']).isOnline():
            updated_friends.append(friends[i])
    return updated_friends

def print_list_of_dicts(lst: List[dict]) -> None:
    print("\n".join([str(d) for d in lst]))

def main():
    set_api_keys()

    args = [arg.lower() for arg in sys.argv]
    just_online_friends = 'all' not in args
    find_friends_of_friends = 'friendsoffriends' in args
    args = list_subtract(args, ['all', 'friendsoffriends'])

    player = create_player_object(args[1])
    print("fyi, the uuid of the player you're getting friends of is " + player.getUUID())

    playerFriendsUUIDS = list(reversed(player.getUUIDsOfFriends()))
    for i in range(2, len(args)):
        friendsExclude = create_player_object(args[i]).getUUIDsOfFriends()
        playerFriendsUUIDS = list_subtract(playerFriendsUUIDS, friendsExclude)

    friends_to_output = iterate_over_friends(playerFriendsUUIDS, just_online_friends)
    if just_online_friends:
        sleep_for_rate_limiting(10)
        friends_to_output = remove_friends_who_logged_off(friends_to_output)
        print("\nDone - online friends:\n")
    else:
        print("\nDone - all friends:\n")

    print_list_of_dicts(friends_to_output)

if __name__ == '__main__':
    main()