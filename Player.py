from __future__ import annotations

from typing import Optional, List, Union, Dict
from copy import deepcopy

import Utils
import hypixel
from MyClasses import UUID_Plus_Time, Specs
import Files

class Player:

    @classmethod
    def make_player_from_json_textfile(cls, filepath: str, uuid_or_ign: str, 
                                       specs: Optional[Specs] = None) -> Player:
        dict_from_file = Files.read_json_textfile(filepath)
        dict_for_player = Utils.find_dict_for_given_player(dict_from_file, uuid_or_ign)
        if not dict_for_player and Utils.is_ign(uuid_or_ign):
            # Possible nothing was found since the given json only contains the uuid for the player,
            # and not their ign. So try again by passing in their uuid.
            dict_for_player = Utils.find_dict_for_given_player(dict_from_file, 
                                                               hypixel.get_uuid(uuid_or_ign))
        assert dict_for_player
        return Player(uuid=dict_for_player['uuid'], 
                      friends=[
                                  UUID_Plus_Time(d['uuid'], d.get('time', None))
                                  for d in dict_for_player.get('friends', [])
                              ],
                      specs=specs
                     )

    def __init__(self, uuid: str, time_friended_parent_player: Union[str, float, int, None] = None,
                 hypixel_object: Optional[hypixel.Player] = None, name: Optional[str] = None, 
                 friends: Union[List[UUID_Plus_Time], List[Player], None] = None, specs: Optional[Specs] = None,
                 name_for_file_output: Optional[str] = None, will_exclude_friends: bool = False,
                 date_cutoff_for_friends: Optional[str] = None, will_intersect: bool = False):
        self._uuid_plus_time = UUID_Plus_Time(uuid, time_friended_parent_player)
        self._hypixel_object = hypixel_object
        self._name = name
        self._specs = deepcopy(specs)
        self._name_for_file_output = name_for_file_output
        self._will_exclude_friends = will_exclude_friends
        self._will_intersect = will_intersect
        self._date_cutoff_for_friends = date_cutoff_for_friends
        self._friends: Optional[List[Player]] = None
        self._call_api_if_friends_empty_in_friends_getter: bool = True
        if friends is not None:
            self._set_friends(friends)
    
    def hypixel_object(self) -> hypixel.Player:
        if not self._hypixel_object:
            self._hypixel_object = hypixel.Player(self.uuid())
        return self._hypixel_object

    def uuid(self) -> str:
        return self._uuid_plus_time.uuid()
    
    def time_friended_parent_player(self, format: str) -> Union[str, float, int, None]:
        """format must be 'ms', 's' or 'date' 
        Function will return the time the player friended the parent player. 
        If there is no parent player (e.g., if player is the root player), None is returned."""
        if format == 'ms':
            return self._uuid_plus_time.time_epoch_in_milliseconds()
        elif format == 's':
            return self._uuid_plus_time.time_epoch_in_seconds()
        elif format == 'date':
            return self._uuid_plus_time.date_string()
        else:
            raise ValueError("Invalid value for 'format' parameter.")
    
    def name(self) -> str:
        if not self._name:
            self._name = self.hypixel_object().getName()
        return self._name
    
    def name_for_file_output(self) -> str:
        assert self._name_for_file_output is not None
        return self._name_for_file_output
    
    def set_name_for_file_output(self, name: str) -> None:
        self._name_for_file_output = name

    def friends(self) -> List[Player]:
        if not self._friends and self._call_api_if_friends_empty_in_friends_getter:
            self._set_friends(self.hypixel_object().getFriends())
        return self._friends if self._friends is not None else []
    
    def specs(self) -> Specs:
        assert self._specs is not None
        return deepcopy(self._specs)
    
    def root_player(self) -> bool:
        return self.specs().root_player()
    
    def friend_of_root_player(self) -> bool:
        return self.specs().friend_of_root_player()
    
    def get_fkdr(self) -> float:
        return self.hypixel_object().getFKDR()
    
    def get_bw_star(self) -> int:
        return self.hypixel_object().getBedwarsStar()
    
    def specs_for_friends(self) -> Optional[Specs]:
        return self.specs().specs_for_friends()
    
    def represents_same_person(self, other: Player) -> bool:
        return self.uuid() == other.uuid()
    
    def set_specs(self, specs: Specs) -> None:
        self._specs = specs
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Player):
            raise ValueError("'other' is not an instance of Player.")
        return (len(self.friends()) == len(other.friends()) and self.name() == other.name() and 
                self._specs == other._specs and self.uuid() == other.uuid() and
                self.time_friended_parent_player('date') == other.time_friended_parent_player('date'))
    
    def set_date_cutoff_for_friends(self, date_cutoff: Optional[str]) -> None:
        """Sets self._date_cutoff_for_friends to the param, and then applies it to the friends list"""
        if date_cutoff:
            assert not self.will_exclude_friends()
        self._date_cutoff_for_friends = date_cutoff
        self.remove_friends_added_before_cutoff()
    
    def date_cutoff_for_friends(self) -> Optional[str]:
        return self._date_cutoff_for_friends
    
    def remove_friends_added_before_cutoff(self) -> None:
        assert not self.will_exclude_friends()
        if not self._date_cutoff_for_friends or not self._friends:
            return
        self._friends = [f for f in self._friends if not
                         Utils.is_older(f.time_friended_parent_player('s'), self._date_cutoff_for_friends)]
    
    def remove_duplicate_friends(self) -> None:
        """Pre-condition: friends list must be sorted in the order you want, since duplicates coming after any 
        originals will be removed. By a 'duplicate', this means a Player object with the same uuid."""
        assert self._friends is not None
        self._set_friends([f for i, f in enumerate(self.friends()) if not f.in_player_list(self.friends()[:i])])
    
    def _set_friends(self, friends: Union[List[UUID_Plus_Time], List[Player], None]) -> None:
        """Note that after this function has been called, if self.friends() is called later and
        self._friends happens to be None or [], the hypixel api won't be called to populate self._friends. 
        The reasoning for this is that since self._set_friends() is being called now, it's assumed the
        caller wants self._friends to be equal to a certain value -- and None or [] are valid values
        if that's what the caller wants."""

        self._call_api_if_friends_empty_in_friends_getter = False
        if not friends:
            self._friends = None if friends is None else []
            # Above line instead of direct assignment in order to satisfy mypy.
            return
        self._friends = []
        for friend in deepcopy(friends):
            if isinstance(friend, UUID_Plus_Time):
                self._friends.append(Player(friend.uuid(),
                                            time_friended_parent_player=friend.time_epoch_in_seconds()))
            else:
                self._friends.append(friend)
            specs_for_friends = self.specs_for_friends()
            assert isinstance(specs_for_friends, Specs)
            self._friends[len(self._friends)-1].set_specs(specs_for_friends)
        if not self.will_exclude_friends():
            self.remove_friends_added_before_cutoff()
    
    def will_exclude_friends(self) -> bool:
        """Returns whether this player's friends are meant to be excluded, as specified in command line args."""
        return self._will_exclude_friends
    
    def set_will_exclude_friends(self, exclude_friends: bool) -> None:
        if exclude_friends:
            assert not self._date_cutoff_for_friends
        self._will_exclude_friends = exclude_friends
    
    def will_intersect(self) -> bool:
        """Returns whether this player's friends will be intersected with the friends (or exclude friends) 
           list leading up to it in combine_players."""
        return self._will_intersect

    def set_will_intersect(self, will_intersect: bool) -> None:
        self._will_intersect = will_intersect
    
    def in_player_list(self, players: List[Player]) -> bool:
        """Returns whether the player is already represented in this players list."""
        return any(self.represents_same_person(p) for p in players)
    
    def create_dictionary_report(self, sort_final_result_by_fkdr: bool = True, 
                                 extra_online_check: bool = False, should_terminate: bool = True) -> dict:
        # CONTINUE HERE - later, could make a Report class and return an object of that, instead of a dict here.
        if self.root_player():
            assert not self.time_friended_parent_player('date')
        if (self.specs().required_online() and 
            not self.hypixel_object().isOnline(extra_online_check=extra_online_check)):
            return {}

        report = {}
        if not self.specs().just_uuids():
            report.update({'name': self.name(), 'fkdr': self.get_fkdr(), 'star': self.get_bw_star()})
        report['uuid'] = self.uuid()
        if time := self.time_friended_parent_player('ms' if Specs.does_program_display_time_as_unix_epoch() 
                                                    else 'date'):
            report['time'] = time
        if self.specs().print_player_data_exclude_friends():
            print(str(report))
        if not self.specs_for_friends():
            return report
        
        self.iterate_over_friends_for_report(report, self.friends(), not should_terminate, 
                                             sort_final_result_by_fkdr, False, True)

        return self.polish_dictionary_report(report, sort_final_result_by_fkdr) if self.root_player() else report
    
    def iterate_over_friends_for_report(self, report: dict, friends: List[Player],
                                        do_additional_passes: bool, sort_final_result_by_fkdr: bool,
                                        on_perpetual_pass: bool, on_first_pass: bool,
                                        end_index: Optional[int] = None) -> None:
        """Will modify `report`, which is passed by reference."""

        # For friends whose online status is shown, there will be some false negatives over time.
        # This is because if their json shows them not online at the start of the program, it won't
        # double check if they're currently online.

        # For friends whose online status isn't shown, there will be some false positives over time.
        # This is because a player's stats could have been updated, but then later on they logged out.

        assert not (on_first_pass and on_perpetual_pass)
        if do_additional_passes:
            assert on_first_pass and self.root_player()

        if 'friends' not in report:
            report['friends'] = [] # list of dicts
        points_to_do_second_passes = [100 * 2**i for i in range(0, 11)]

        for i in range(len(friends) if end_index is None else end_index+1):
            if i in points_to_do_second_passes and on_first_pass and do_additional_passes:
                # Do a 'second pass' from 0 until i-1 indexed players, checking if their stats
                # have been updated (for players who don't have the online status shown):
                self.iterate_over_friends_for_report(report, friends, False, sort_final_result_by_fkdr,
                                                     False, False, end_index=i-1)
            assert isinstance(report['friends'], list)
            friend: Player = friends[i]
            if friend.uuid() not in [d['uuid'] for d in report['friends']]:
                if friend_report := friend.create_dictionary_report(extra_online_check = not on_first_pass):
                    report['friends'].append(friend_report)
            self.processed_msg(i+1, on_perpetual_pass, on_first_pass)

        if do_additional_passes:
            # Do perpetual passes:
            while True:
                self.polish_dictionary_report(report, sort_final_result_by_fkdr)
                report['friends'] = []
                self.iterate_over_friends_for_report(report, friends, False,
                                                     sort_final_result_by_fkdr, True, False)
    
    def processed_msg(self, num_processed: int, on_perpetual_pass: bool, on_first_pass: bool) -> None:
        """Prints a message saying how many players have been processed, if the number is a multiple of 20,
           and if the player is the root player."""
        if num_processed % 20 != 0 or not self.root_player():
            return
        print("Processed " + str(num_processed), end="")
        if on_perpetual_pass:
            print(" for a perpetual pass")
        elif not on_first_pass:
            print(" for a 'second pass'")
        else:
            print()

    def polish_dictionary_report(self, report: dict, sort_by_fkdr: bool) -> dict:
        report = deepcopy(report)
        if 'friends' in report:
            report['friends'] = sorted(report['friends'], 
                                key=lambda d: d.get('fkdr' if sort_by_fkdr else 'star', 0), 
                                reverse=True)
            # Remove duplicates for any uuids (friends) - however, shouldn't be any:
            friends_copy = report['friends']
            report['friends'] = list({f['uuid']:f for f in report['friends']}.values())
            assert friends_copy == report['friends']
        if self.specs().print_only_players_friends():
            Utils.print_list(report['friends'], prepended_msg="\n\n", separator="\n")
        return report
    
    def polish_friends_list(self, friends_to_exclude: Union[List[Player], Dict[str, Player]]) -> None:
        """Will sort friends, remove duplicates, and remove any who appear in the friends_to_exclude param.
        Note that a Player object is treated as an equivalent/duplicate player if it has the same uuid as
        another Player. Other details (such as time friended parent player) can differ."""
        assert self._friends is not None
        self.remove_friends_added_before_cutoff() # Probably redundant
        self._set_friends(sorted(self.friends(), key=lambda f: f.time_friended_parent_player('s') or 0, reverse=True))
        self.remove_duplicate_friends()
        if isinstance(friends_to_exclude, List):
            self._set_friends([f for f in self.friends() if not f.in_player_list(friends_to_exclude)])
        elif isinstance(friends_to_exclude, dict):
            self._set_friends([f for f in self.friends() if not f.uuid() in friends_to_exclude])
        else:
            raise ValueError("friends_to_exclude must be a list or dict of Players")
    
    def diff_f_lists(self, other: Player, print_results: bool = False) -> List[Player]:
        diff = [f for f in self.friends() if not f.in_player_list(other.friends())]
        if print_results:
            print(str(len(diff)) + " friends of " + self.name() + " and not of " + other.name() + ":")
            for player in diff:
                player.print_uuid_name()
            print('\n\n')
        return diff
    
    def print_uuid_name(self) -> None:
        print('name: ' + self.name() + ', uuid: ' + self.uuid())