from __future__ import annotations

import datetime
import time
from typing import Optional

class UUID_Plus_Time:
    """This class encapsulates a UUID and a time (unix epoch), likely representing when
    they were added to another player."""
    def __init__(self, uuid: str, unix_epoch_milliseconds: Optional[float] = None, 
                 unix_epoch_seconds: Optional[float] = None, date_string: Optional[str] = None):
        assert 1 >= sum([unix_epoch_milliseconds is not None, unix_epoch_seconds is not None, date_string is not None])
        self._uuid = uuid
        if unix_epoch_milliseconds is not None:
            self._unix_epoch_seconds = unix_epoch_milliseconds / 1000
        elif unix_epoch_seconds is not None:
            self._unix_epoch_seconds = unix_epoch_seconds
        elif date_string is not None:
            self._unix_epoch_seconds = time.mktime(datetime.datetime.strptime(date_string, '%Y-%m-%d').timetuple())
        else:
            self._unix_epoch_seconds = None
    
    def uuid(self) -> str:
        return self._uuid

    def time_epoch_in_seconds(self) -> Optional[float]:
        return self._unix_epoch_seconds
    
    def time_epoch_in_milliseconds(self) -> Optional[float]:
        """Returns the time as a float representing the unix epoch time in milliseconds"""
        if self._unix_epoch_seconds is None:
            return None
        return self._unix_epoch_seconds * 1000
    
    def date_string(self) -> Optional[str]:
        """Returns the time as a YYYY-MM-DD date string"""
        if self._unix_epoch_seconds is None:
            return None
        return datetime.datetime.utcfromtimestamp(self._unix_epoch_seconds).strftime('%Y-%m-%d')
    
    def no_time(self) -> bool:
        return self._unix_epoch_seconds is None
    
    def sort_key(self) -> float:
        if self.no_time():
            return 0
        return self.time_epoch_in_milliseconds()
    
    def same_person(self, other: "UUID_Plus_Time") -> bool:
        return self._uuid == other.uuid()

class Specs:
    """This class represents specifications that a caller has when it calls the 
       create_dictionary_report_for_player function."""

    _common_specs: dict = {'print player data': None, 'set flag': False}
    
    @classmethod
    def set_common_specs(cls, print_player_data: bool) -> None:
        assert not cls._common_specs['set flag']
        cls._common_specs['print player data'] = print_player_data
        cls._common_specs['set flag'] = True
    
    @classmethod
    def is_common_specs_initialized(cls) -> bool:
        return cls._common_specs['set flag']
    
    @classmethod
    def does_program_print_player_data(cls) -> bool:
        return cls._common_specs['print player data']

    def __init__(self, include_players_name_and_fkdr: bool, player_must_be_online: bool,
                 friends_specs: Optional[Specs], degrees_from_original_player: int):
        assert Specs._common_specs['set flag']
        self._include_players_name_and_fkdr = include_players_name_and_fkdr
        self._player_must_be_online = player_must_be_online
        self._friends_specs = friends_specs
        self._degrees_from_original_player = degrees_from_original_player
    
    def include_name_fkdr(self) -> bool:
        return self._include_players_name_and_fkdr
    
    def required_online(self) -> bool:
        return self._player_must_be_online
    
    def specs_for_friends(self) -> Optional[Specs]:
        return self._friends_specs
    
    def degrees_from_root_player(self) -> int:
        return self._degrees_from_original_player
    
    def root_player(self) -> bool:
        return self._degrees_from_original_player == 0
    
    def friend_of_root_player(self) -> bool:
        return self._degrees_from_original_player == 1
    
    def print_player_data_exclude_friends(self) -> bool:
        return Specs._common_specs['print player data'] and self.friend_of_root_player()
    
    def print_only_players_friends(self) -> bool:
        return Specs._common_specs['print player data'] and self.root_player()