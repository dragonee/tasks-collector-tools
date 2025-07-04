"""Pydantic models for tasks collector tools."""

from datetime import datetime, date
from typing import List, Optional, Literal, Union
from pydantic import BaseModel


def not_empty(text):
    return text and text.strip() != '' and text.strip() != '?'


class BaseEvent(BaseModel):
    id: int
    published: datetime
    resourcetype: str


class Habit(BaseModel):
    id: int
    name: str
    description: Optional[str]
    slug: str
    tagname: str


class JournalAdded(BaseEvent):
    resourcetype: Literal['JournalAdded']
    comment: str
    tags: List[str]


class HabitTracked(BaseEvent):
    resourcetype: Literal['HabitTracked']
    note: str
    occured: bool
    habit: Habit


class ObservationEvent(BaseEvent):
    url: str


class ObservationMade(ObservationEvent):
    resourcetype: Literal['ObservationMade']
    event_stream_id: str
    type: str
    situation: str
    interpretation: Optional[str]
    approach: Optional[str]


class ObservationUpdated(ObservationEvent):
    resourcetype: Literal['ObservationUpdated']
    event_stream_id: str
    observation_id: Optional[int]
    situation_at_creation: str
    comment: str


class ObservationRecontextualized(ObservationEvent):
    resourcetype: Literal['ObservationRecontextualized']
    event_stream_id: str
    situation: str
    old_situation: str


class ObservationReinterpreted(ObservationEvent):
    resourcetype: Literal['ObservationReinterpreted']
    event_stream_id: str
    interpretation: Optional[str]
    old_interpretation: Optional[str]
    situation_at_creation: str


class ObservationReflectedUpon(ObservationEvent):
    resourcetype: Literal['ObservationReflectedUpon']
    event_stream_id: str
    approach: Optional[str]
    old_approach: Optional[str]
    situation_at_creation: str


class ObservationClosed(ObservationEvent):
    resourcetype: Literal['ObservationClosed']
    event_stream_id: str
    type: str
    situation: str
    interpretation: Optional[str]
    approach: Optional[str]


class Plan(BaseModel):
    id: int
    focus: str
    want: str
    pub_date: date

    def empty(self):
        return not self.has_want() and not self.has_focus()

    def has_want(self):
        return not_empty(self.want)

    def has_focus(self):
        return not_empty(self.focus)


class Reflection(BaseModel):
    id: int
    good: str
    better: str
    best: str
    pub_date: date

    def empty(self):
        return not self.has_good() and not self.has_better() and not self.has_best()

    def has_good(self):
        return not_empty(self.good)
    
    def has_better(self):
        return not_empty(self.better)
    
    def has_best(self):
        return not_empty(self.best)


Event = Union[
    JournalAdded, 
    HabitTracked, 
    ObservationMade, 
    ObservationUpdated, 
    ObservationRecontextualized, 
    ObservationReinterpreted, 
    ObservationReflectedUpon, 
    ObservationClosed
]

class Result(BaseModel):
    date: date
    events: List[Event]
    plan: Optional[Plan]
    reflection: Optional[Reflection]

    def empty(self):
        if self.events:
            return False
        
        if self.plan and not self.plan.empty():
            return False
        
        if self.reflection and not self.reflection.empty():
            return False
        
        return True 