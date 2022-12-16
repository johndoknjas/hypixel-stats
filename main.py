import os
import os.path
import sys
from hypixelpy import hypixel
import time
from typing import List, Union, Optional
import json
import os

# CONTINUE HERE - todos:
    # Refactor the main function a little bit to get rid of code duplication.

    # Maybe do an overlay.

def fkdr_division(final_kills: int, final_deaths: int) -> float:
    return final_kills / final_deaths if final_deaths else float(final_kills)

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
    if 'stats' not in player.JSON or 'Bedwars' not in player.JSON['stats']:
        return 0.0
    return fkdr_division(player.JSON['stats']['Bedwars'].get('final_kills_bedwars', 0), 
                         player.JSON['stats']['Bedwars'].get('final_deaths_bedwars', 0))

def iterate_over_friends(playerFriendsUUIDS, just_online_friends: bool, just_uuids_of_friends: bool) -> List[dict]:
    if just_uuids_of_friends and not just_online_friends:
        # Caller only wants the uuids, and no work has to be done to check whether each friend is online.
        # So, can just put the passed in uuids of friends into a List of dicts and return.
        uuids = []
        for uuid in playerFriendsUUIDS:
            uuids.append({'UUID': uuid})
        return uuids
    
    friends_data = []
    for i, uuid in enumerate(playerFriendsUUIDS):
        if i % 10 == 0:
            print("Processed " + str(i))
        friend = hypixel.Player(uuid)
        if just_online_friends and not friend.isOnline():
            continue
        data = {'name': friend.getName(), 'FKDR': calculate_fkdr(friend), 'UUID': friend.getUUID()}
        print(str(data))
        friends_data.append(data)
    return sorted(friends_data, key=lambda d: d['FKDR'], reverse=True)

def remove_friends_who_logged_off(friends: List[dict]) -> List[dict]:
    return [friend for friend in friends if hypixel.Player(friend['UUID']).isOnline()]

def print_list_of_dicts(lst: List[dict]) -> None:
    print("\n".join([str(d) for d in lst]))

def write_data_as_json_to_file(data: Union[dict, List], description: str = "") -> None:
    filename = os.path.join("results", description + " - " + str(time.time_ns()) + ".txt")
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(json.dumps(data, indent=4))

def main():
    set_api_keys()

    args = [arg.lower() for arg in sys.argv]
    just_uuids_of_friends = 'justuuidsoffriends' in args
    just_online_friends = 'all' not in args
    find_friends_of_friends = 'friendsoffriends' in args
    args = list_subtract(args, ['all', 'friendsoffriends', 'justuuidsoffriends'])

    player = create_player_object(args[1])
    playerName = player.getName()
    print("fyi, the uuid of the player you're getting friends of is " + player.getUUID())

    playerFriendsUUIDS = list(reversed(player.getUUIDsOfFriends()))
    for i in range(2, len(args)):
        friendsExclude = create_player_object(args[i]).getUUIDsOfFriends()
        playerFriendsUUIDS = list_subtract(playerFriendsUUIDS, friendsExclude)

    friends_to_output = iterate_over_friends(playerFriendsUUIDS, just_online_friends, just_uuids_of_friends)
    if just_online_friends:
        friends_to_output = remove_friends_who_logged_off(friends_to_output)
        print("\nDone - online friends:\n")
    else:
        print("\nDone - all friends:\n")
        list_for_file_output = [
            {
                'name': playerName,
                'uuid': player.getUUID(), 
                'fkdr': calculate_fkdr(player),
                'friends': friends_to_output
            }
        ]
        write_data_as_json_to_file(list_for_file_output, "Stats of friends for " + playerName)
    print_list_of_dicts(friends_to_output)

    if find_friends_of_friends:
        list_for_file_output = [] # Will be a list of many dicts
        for i, friend_uuid in enumerate(playerFriendsUUIDS):
            # Get just the uuids for all of this friend's friends.
            if i % 50 == 0 and i > 0:
                print("Retrieved UUIDS of " + str(i) + " friends' friends")
            friend = hypixel.Player(friend_uuid)
            friends_of_friend = iterate_over_friends(list(reversed(friend.getUUIDsOfFriends())), False, True)
            list_for_file_output.append(
                {
                    'name': friend.getName(),
                    'uuid': friend.getUUID(), 
                    'fkdr': calculate_fkdr(friend),
                    'friends': friends_of_friend
                }
            )
        write_data_as_json_to_file(list_for_file_output, "Friends of friends of " + playerName)


if __name__ == '__main__':
    main()