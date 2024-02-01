# API for Metabotnik

GET /api/v1/xy/<id>/<float>_<float> Returns the filename of entry at that point, for the metabotnik specified by <id> id can be [A-Za-z_]

For example: /api/v1/xy/foobarbaz/0.212_0.5 which then returns the string: "abc" as a text/plain response

We are adding this to enable the semantic navigaiton for large metabotniks, for example the NCO Front page image.
Doing it as an API, as we need to bootstrap this as a service used by many other projects.

For now, we have left the creation of the input data .sqlite file out of scope, and have baked it in to the bootstrap process of runniung this MVP container.
Next step required is mapping how we create these files.
For an example of an import process on how this is done, see the LCI script at: `/home/devops/Dropbox/lci/read_main_metabotnik.py`

## Database Schema

CREATE TABLE projects (name TEXT PRIMARY KEY, width INTEGER, height INTEGER);
CREATE TABLE <projectname>\_objs (id INTEGER PRIMARY KEY AUTOINCREMENT, obj);
CREATE VIRTUAL TABLE <projectname>\_index USING rtree(id, x1, x2, y1, y2)
