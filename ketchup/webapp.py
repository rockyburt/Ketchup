import asyncio

from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from quart import Quart

from ketchup import base
from ketchup.gqlschema import schema
from ketchup.strawview import GraphQLView

app = Quart("ketchup")
app.config.from_object(base.config)


app.add_url_rule("/graphql", view_func=GraphQLView.as_view("graphql_view", schema=schema))


@app.route("/")
async def index():
    return 'Welcome to Ketchup!  Please see <a href="/graphql">Graph<em>i</em>QL</a> to interact with the GraphQL endpoint.'


def hypercorn_serve():
    hypercorn_config = HypercornConfig()
    hypercorn_config.bind = ["0.0.0.0:5000"]
    hypercorn_config.use_reloader = True
    asyncio.run(serve(app, hypercorn_config, shutdown_trigger=lambda: asyncio.Future()))


if __name__ == "__main__":
    hypercorn_serve()
