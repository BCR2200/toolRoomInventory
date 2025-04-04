import datetime
from pathlib import Path
from typing import Optional, Self, Tuple


class Tool:
    def __init__(self, tool_id: Optional[int], name: str, barcode: Optional[str],
                 description: str, picture: Optional[Path], signed_out: bool,
                 holder_id: Optional[int], signed_out_since: Optional[datetime.datetime]):
        self.tool_id = tool_id
        self.name = name
        self.barcode = barcode
        self.description = description
        self.picture = picture
        self.signed_out = signed_out
        self.holder_id = holder_id
        self.signed_out_since = signed_out_since

    def __repr__(self):
        return (f"Tool(tool_id={self.tool_id}, name={self.name}, barcode={self.barcode}, "
                f"description={self.description}, picture={self.picture}, "
                f"signed_out={self.signed_out}, holder_id={self.holder_id}, "
                f"signed_out_since={self.signed_out_since})")

    @property
    def signed_out_since_human(self):
        return self.signed_out_since.astimezone().strftime("%Y-%m-%d %H:%M")

    @property
    def barcode_url(self):
        if self.barcode is None:
            return None
        # TODO const refactor
        return f"bar_{self.barcode}.png"

    @property
    def picture_url(self):
        if self.picture is None:
            return None
        return self.picture

    @classmethod
    def from_row(cls, row) -> Self:
        if row is None:
            raise ValueError('No row returned')
        path = None
        if row[4] is not None:
            path = Path(row[4])
        holder_id = None
        if row[6] is not None:
            holder_id = int(row[6])
        since = None
        if row[7] is not None:
            since = cls.parse_db_signed_out_since(row[7])
        return cls(int(row[0]), row[1], row[2], row[3], path, bool(row[5]), holder_id, since)

    def to_row_and_projection(self) -> Tuple[Tuple, Tuple[str, str]]:
        col_names = ['id', 'name', 'barcode', 'description', 'picture', 'signed_out', 'holder_id', 'signed_out_since']
        col_markers = ['?', '?', '?', '?', '?', '?', '?', '?']
        projection = (
            f"({','.join(col_names)})",
            f"({','.join(col_markers)})",
        )
        row = (self.tool_id, self.name, self.barcode, self.description, self.picture, self.signed_out, self.holder_id, self.signed_out_since)

        return row, projection

    @staticmethod
    def default_projection() -> list[str]:
        return ["id", "name", "barcode", "description", "picture", "signed_out", "holder_id", "signed_out_since"]

    @staticmethod
    def db_format_signed_out_since(since: datetime.datetime) -> str:
        return since.isoformat()

    @staticmethod
    def parse_db_signed_out_since(since: str) -> datetime.datetime:
        return datetime.datetime.fromisoformat(since)
