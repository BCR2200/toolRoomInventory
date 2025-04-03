from typing import Optional, Self, Tuple


class User:
    def __init__(self, user_id: int, name: str, barcode: Optional[str],
                 is_admin: bool, is_user: bool):
        self.user_id = user_id
        self.name = name
        self.barcode = barcode
        self.is_admin = is_admin
        self.is_user = is_user

    def __repr__(self):
        return f"User(user_id={self.user_id}, name={self.name}, barcode={self.barcode}, is_admin={self.is_admin}, is_user={self.is_user})"

    @property
    def roles(self):
        roles = []
        if self.is_admin:
            roles.append("Admin")
        if self.is_user:
            roles.append("User")
        # TODO const refactor
        return ", ".join(roles)

    @property
    def barcode_url(self):
        if self.barcode is None:
            return None
        # TODO const refactor
        return f"bar_{self.barcode}.png"

    @classmethod
    def from_row(cls, row) -> Self:
        if row is None:
            raise ValueError('No row returned')
        return cls(int(row[0]), row[1], row[2], bool(row[3]), bool(row[4]))

    @staticmethod
    def default_projection() -> list[str]:
        return ["id", "name", "barcode", "is_admin", "is_user"]

    def to_row_and_projection(self) -> Tuple[Tuple, Tuple[str, str]]:
        col_names = ['id', 'name', 'barcode', 'is_admin', 'is_user']
        col_markers = ['?', '?', '?', '?', '?']
        projection = (
            f"({','.join(col_names)})",
            f"({','.join(col_markers)})",
        )
        row = (self.user_id, self.name, self.barcode, self.is_admin, self.is_user)

        return row, projection
