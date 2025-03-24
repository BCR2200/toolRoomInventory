from typing import Self


class User:
    def __init__(self, user_id: int, name: str, is_admin: bool, is_user: bool):
        self.user_id = user_id
        self.name = name
        self.is_admin = is_admin
        self.is_user = is_user

    def __repr__(self):
        return f"User(user_id={self.user_id}, name={self.name}, is_admin={self.is_admin}, is_user={self.is_user})"

    @classmethod
    def from_row(cls, row) -> Self:
        if row is None:
            raise ValueError('No row returned')
        return cls(int(row[0]), row[1], bool(row[2]), bool(row[3]))

    @staticmethod
    def default_projection() -> list[str]:
        return ["id", "name", "is_admin", "is_user"]