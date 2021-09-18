import strawberry


@strawberry.type
class Query:
    @strawberry.field
    def upper(self, val: str) -> str:
        return val.upper()
