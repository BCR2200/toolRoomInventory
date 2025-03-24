import datetime
from pathlib import Path
from typing import Optional


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