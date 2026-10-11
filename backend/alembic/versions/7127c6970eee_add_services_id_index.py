
"""Keep the services ID index migration in history.

The initial migration already creates ix_services_id,
so this migration intentionally performs no schema changes.
"""

from typing import Sequence, Union

revision: str = "7127c6970eee"
down_revision: Union[str, Sequence[str], None] = "8715065c7435"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ix_services_id is already created by the initial migration.
    pass


def downgrade() -> None:
    # The initial migration owns this index.
    pass
