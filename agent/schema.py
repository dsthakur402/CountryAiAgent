from pydantic import BaseModel, Field

# fields the user might ask about. Keep this list in sync with FIELD_MAP
# in countries_api.py - the intent layer shouldn't ask for things the
# API layer can't resolve.
SUPPORTED_FIELDS = [
    "population",
    "capital",
    "currency",
    "languages",
    "area",
    "region",
    "subregion",
    "timezones",
    "borders",
    "flag",
]


class Intent(BaseModel):
    countries: list[str] = Field(
        default_factory=list,
        description="Country names mentioned in the question, in the order they appear.",
    )
    fields: list[str] = Field(
        default_factory=list,
        description=(
            "Which attributes the user wants. Must be a subset of: "
            + ", ".join(SUPPORTED_FIELDS)
            + ". Use an empty list if the user wants a general overview."
        ),
    )
