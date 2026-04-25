from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import json


@dataclass
class Door:
    id: str
    connects: List[str]
    width: float
    position: Tuple[float, float] = (0.0, 0.0)
    is_exit: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "connects": self.connects,
            "width": self.width,
            "position": list(self.position),
            "is_exit": self.is_exit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Door":
        pos = data.get("position", [0, 0])
        return cls(
            id=data["id"],
            connects=data.get("connects", []),
            width=data.get("width", 0.9),
            position=(pos[0], pos[1]),
            is_exit=data.get("is_exit", False),
        )


@dataclass
class Exit:
    id: str
    room_id: str
    position: Tuple[float, float] = (0.0, 0.0)
    width: float = 1.2
    leads_outside: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "room_id": self.room_id,
            "position": list(self.position),
            "width": self.width,
            "leads_outside": self.leads_outside,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Exit":
        pos = data.get("position", [0, 0])
        return cls(
            id=data["id"],
            room_id=data.get("room_id", ""),
            position=(pos[0], pos[1]),
            width=data.get("width", 1.2),
            leads_outside=data.get("leads_outside", True),
        )


@dataclass
class Wall:
    id: str
    start: Tuple[float, float]
    end: Tuple[float, float]
    room_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start": list(self.start),
            "end": list(self.end),
            "room_id": self.room_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Wall":
        return cls(
            id=data["id"],
            start=tuple(data["start"]),
            end=tuple(data["end"]),
            room_id=data.get("room_id", ""),
        )


@dataclass
class Room:
    id: str
    name: str
    type: str
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    area: float = 0.0
    occupancy: int = 0
    floor: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "polygon": [list(p) for p in self.polygon],
            "area": self.area,
            "occupancy": self.occupancy,
            "floor": self.floor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Room":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            type=data.get("type", "office"),
            polygon=[tuple(p) for p in data.get("polygon", [])],
            area=data.get("area", 0.0),
            occupancy=data.get("occupancy", 0),
            floor=data.get("floor", 0),
        )


@dataclass
class Corridor:
    id: str
    name: str
    width: float
    length: float
    connects: List[str] = field(default_factory=list)
    polygon: List[Tuple[float, float]] = field(default_factory=list)
    floor: int = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "length": self.length,
            "connects": self.connects,
            "polygon": [list(p) for p in self.polygon],
            "floor": self.floor,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Corridor":
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            width=data.get("width", 1.4),
            length=data.get("length", 0.0),
            connects=data.get("connects", []),
            polygon=[tuple(p) for p in data.get("polygon", [])],
            floor=data.get("floor", 0),
        )


@dataclass
class FloorPlan:
    id: str
    name: str
    floor: int = 0
    rooms: List[Room] = field(default_factory=list)
    corridors: List[Corridor] = field(default_factory=list)
    doors: List[Door] = field(default_factory=list)
    exits: List[Exit] = field(default_factory=list)
    walls: List[Wall] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "floor": self.floor,
            "rooms": [r.to_dict() for r in self.rooms],
            "corridors": [c.to_dict() for c in self.corridors],
            "doors": [d.to_dict() for d in self.doors],
            "exits": [e.to_dict() for e in self.exits],
            "walls": [w.to_dict() for w in self.walls],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FloorPlan":
        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", "Unnamed Plan"),
            floor=data.get("floor", 0),
            rooms=[Room.from_dict(r) for r in data.get("rooms", [])],
            corridors=[Corridor.from_dict(c) for c in data.get("corridors", [])],
            doors=[Door.from_dict(d) for d in data.get("doors", [])],
            exits=[Exit.from_dict(e) for e in data.get("exits", [])],
            walls=[Wall.from_dict(w) for w in data.get("walls", [])],
        )

    @classmethod
    def load_from_json(cls, filepath: str) -> "FloorPlan":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_json(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def total_occupancy(self) -> int:
        return sum(r.occupancy for r in self.rooms)

    def get_room(self, room_id: str) -> Optional[Room]:
        for r in self.rooms:
            if r.id == room_id:
                return r
        return None

    def get_corridor(self, corridor_id: str) -> Optional[Corridor]:
        for c in self.corridors:
            if c.id == corridor_id:
                return c
        return None
