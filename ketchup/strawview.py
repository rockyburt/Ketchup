import json
import logging
import pathlib
import traceback
from typing import Any, Union

import strawberry
from quart import Response, abort, render_template_string, request
from quart.typing import ResponseReturnValue
from quart.views import View
from strawberry.exceptions import MissingQueryError
from strawberry.file_uploads.utils import replace_placeholders_with_files
from strawberry.http import GraphQLHTTPResponse, parse_request_data, process_result
from strawberry.schema import BaseSchema
from strawberry.types import ExecutionResult

logger = logging.getLogger("ketchup")


def render_graphiql_page() -> str:
    dir_path = pathlib.Path(strawberry.__file__).absolute().parent
    graphiql_html_file = f"{dir_path}/static/graphiql.html"

    html_string = None

    with open(graphiql_html_file, "r") as f:
        html_string = f.read()

    return html_string.replace("{{ SUBSCRIPTION_ENABLED }}", "false")


class GraphQLView(View):
    methods = ["GET", "POST"]

    def __init__(self, schema: BaseSchema, graphiql: bool = True):
        self.schema = schema
        self.graphiql = graphiql

    async def process_result(self, result: ExecutionResult) -> GraphQLHTTPResponse:
        if result.errors:
            for error in result.errors:
                err = getattr(error, "original_error", None) or error
                formatted = "".join(traceback.format_exception(err.__class__, err, err.__traceback__))
                logger.error(formatted)

        return process_result(result)

    async def dispatch_request(self, *args: Any, **kwargs: Any) -> Union[ResponseReturnValue, str]:
        if "text/html" in request.headers.get("Accept", ""):
            if not self.graphiql:
                abort(404)

            template = render_graphiql_page()
            return await render_template_string(template)

        content_type = str(request.headers.get("content-type", ""))
        if content_type.startswith("multipart/form-data"):
            form = await request.form
            operations = json.loads(form.get("operations", "{}"))
            files_map = json.loads(form.get("map", "{}"))

            data = replace_placeholders_with_files(operations, files_map, await request.files)
        else:
            data = await request.get_json()

        try:
            request_data = parse_request_data(data)
        except MissingQueryError:
            return Response("No valid query was provided for the request", 400)

        context = {"request": request}

        result = await self.schema.execute(
            request_data.query,
            variable_values=request_data.variables,
            context_value=context,
            operation_name=request_data.operation_name,
            root_value=None,
        )

        response_data = await self.process_result(result)

        return Response(
            json.dumps(response_data),
            status=200,
            content_type="application/json",
        )
