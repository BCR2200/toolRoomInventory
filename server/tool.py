import datetime
from pathlib import Path
from typing import Optional, Self


class Tool:
    def __init__(self, tool_id: int, name: str, description: str, picture: Optional[Path],
                 signed_out: bool, holder_id: int, signed_out_since: datetime.datetime):
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.picture = picture
        self.signed_out = signed_out
        self.holder_id = holder_id
        self.signed_out_since = signed_out_since

    def __repr__(self):
        return f"Tool(tool_id={self.tool_id}, name={self.name}, description={self.description}, picture={self.picture}, signed_out={self.signed_out}, holder_id={self.holder_id}, signed_out_since={self.signed_out_since})"

    @classmethod
    def from_row(cls, row) -> Self:
        if row is None:
            raise ValueError('No row returned')
        path = None
        if row[3] is not None:
            path = Path(row[3])
        holder_id = None
        if row[5] is not None:
            holder_id = int(row[5])
        since = None
        if row[6] is not None:
            since = cls.parse_db_signed_out_since(row[6])
        return cls(int(row[0]), row[1], row[2], path, bool(row[4]), holder_id, since)

    @staticmethod
    def default_projection() -> list[str]:
        return ["id", "name", "is_admin", "is_user"]

    @staticmethod
    def db_format_signed_out_since(since: datetime.datetime) -> str:
        return since.isoformat()

    @staticmethod
    def parse_db_signed_out_since(since: str) -> datetime.datetime:
        return datetime.datetime.fromisoformat(since)
