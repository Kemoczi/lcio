import os
from starlette.applications import Starlette
from starlette.config import Config
from starlette.routing import Route
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.exceptions import HTTPException
import uvicorn
import databases
import string

config = Config(".env")
DATABASE_URL = config("DATABASE_URL", default="sqlite:///db.sqlite3")
DEBUG = config("DEBUG", default=False)
# disable auto-update behavior for metabotnik.brill.com deployment
# database_filename = DATABASE_URL.replace("sqlite:///", "")
# if not os.path.exists(database_filename):
#     r = httpx.get("https://metabotnik.com/api/db.sqlite3")
#     if r.status_code == 200:
#         open(database_filename, "wb").write(r.content)
database = databases.Database(DATABASE_URL)


async def ping(request):
    return PlainTextResponse("pong")


def escape(param):
    # As we need to use string formatting to access a table name, this leaves us open to SQL injection attacks :-(
    # The route to go would be looking into sqlite sql syntax for referencing table names dynamically in the queries
    return "".join(
        [ch for ch in param.lower() if ch in string.ascii_lowercase + string.digits]
    )


async def xy(request):
    projectname = escape(request.path_params["projectname"])
    x = request.path_params["x"]
    y = request.path_params["y"]
    query = (
        "SELECT obj FROM %s_objs WHERE id IN (SELECT id FROM %s_index WHERE x1 <= :x1 AND x2 >= :x2 AND y1 <= :y1 AND y2 >= :y2)"
        % (projectname, projectname)
    )
    results = await database.fetch_all(
        query, values={"x1": x, "x2": x, "y1": y, "y2": y}
    )
    if not results:
        raise HTTPException(status_code=404)

    anid = results[0][0]
    response = PlainTextResponse(
        anid,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
    )

    return response


async def xy_wh(request):
    projectname = escape(request.path_params["projectname"])
    x = request.path_params["x"]
    y = request.path_params["y"]
    query = f"SELECT O.obj, I.x1, I.x2, I.y1, I.y2 FROM {projectname}_objs AS O LEFT JOIN {projectname}_index AS I ON O.id = I.id WHERE I.x1 <= :x1 AND I.x2 >= :x2 AND I.y1 <= :y1 AND I.y2 >= :y2"
    results = await database.fetch_all(
        query, values={"x1": x, "x2": x, "y1": y, "y2": y}
    )
    if not results:
        raise HTTPException(status_code=404)

    obj, x1, x2, y1, y2 = results[0]

    response = JSONResponse(
        {"obj": obj, "x1": x1, "x2": x2, "y1": y1, "y2": y2},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
    )

    return response


async def tag_wh(request):
    projectname = request.path_params["projectname"]
    tag = request.path_params["tag"] + "%"
    query = f"SELECT I.x1, I.x2, I.y1, I.y2 FROM {projectname}_tags AS T LEFT JOIN {projectname}_index AS I ON I.id = T.obj_id WHERE T.tag LIKE :tag"
    results = await database.fetch_all(query, values={"tag": tag})
    if not results:
        raise HTTPException(status_code=404)

    x1, x2, y1, y2 = results[0]

    response = JSONResponse(
        {"x1": x1, "x2": x2, "y1": y1, "y2": y2},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
    )

    return response


async def project(request):
    projectname = request.path_params["projectname"]
    results = await database.fetch_all(
        "SELECT name, width, height FROM projects WHERE name = :projectname",
        values={"projectname": projectname},
    )
    if not results:
        raise HTTPException(status_code=404)

    name, width, height = results[0]

    response = JSONResponse(
        {"name": name, "width": width, "height": height},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
    )

    # Consider adding the number of objects from a count(*) query too.

    return response


async def index(request):
    results = await database.fetch_all("SELECT name FROM projects")
    return PlainTextResponse("Metabotnik API\n%s" % "\n".join([r[0] for r in results]))


async def not_found(request, exc):
    return PlainTextResponse(
        "What you seek is not here",
        status_code=404,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        },
    )


routes = [
    Route("/", index),
    Route("/api/", index),
    Route("/api/ping", ping),
    Route("/api/v1/xy/{projectname}/{x:float}_{y:float}", xy),
    Route("/api/v1/project/{projectname}/", project),
    Route("/api/v1/xy_wh/{projectname}/{x:float}_{y:float}", xy_wh),
    Route("/api/v1/tag_wh/{projectname}/{tag}", tag_wh),
]
exception_handlers = {404: not_found}

app = Starlette(
  routes=routes, 
  exception_handlers=exception_handlers,
  debug=DEBUG,
)

if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8000, reload=DEBUG)
