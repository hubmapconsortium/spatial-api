# HuBMAP Spatial API

This information will help you get the Spatian API up in running whether locally or on an environment.
It is available at
[DEV](https://spatial-api.dev.hubmapconsortium.org/status), and
[PROD](https://spatial.api.hubmapconsortium.org/status).

## Configuration File

The configuration file should be located in `./server/resources/app.properties` for deployment.
There is a `./server/resources/app.example.properties` that you can use as a template for `./server/resources/app.properties`.
The `./server/resources/application.example.properties` assumes that the database is running in
a docker container with a network common to the Spatial API container.
This will likely be the case when running locally (see `scripts/run_local.sh`).

The `./server/resources/app.local.properties` is used by scripts that wish to access the database
running in the local Docker containers.
The notable difference is that when accessing the PostgreSQL server form the container
(as the microservice would do) the database Services name `db` (from `docker-compose.yml`) should be used.
When accessing the database from a script running on the localhost (anything in `scripts`), `localhost` should be used.

Since this microservice accesses a Neo4j, and a PosgreSQL database you will need to provide the server,
user, and password for these.

The `./server/resources/app.properties` should never be saved to GitHUB as it contains passwords.
You should create it on the deployment machine, or locally for testing.


## Build, Publish, Deploy Workflow
These are the steps used to build, publish, and deploy a Docker image.

Before doing so you will need to follow the steps outlined in the section `Configuration File`
to configure the server.

Local deployment instructions for testing purposes are found in the Section `Local Deployment`.

### Get the Latest Code
Login to the deployment server (in this case DEV) and get the latest version of the code from the GitHub repository.
```bash
# Access the server, switch accounts and go to the server directory
$ ssh -i ~/.ssh/id_rsa_e2c.pem cpk36@ingest.dev.hubmapconsortium.org
$ sudo /bin/su - hive
$ cd /opt/hubmap/spatial-api
$ git checkout main
$ git status
# On branch main
...
$ git pull
```
For production the deployment machine is `ingest.hubmapconsortium.org`.
```bash
$ ssh -i ~/.ssh/id_rsa_e2c.pem cpk36@ingest.hubmapconsortium.org
...
```
You should now have the most recent version of the code which should be in the `main` branch.
You can also deploy other branches on DEV for testing.

### Build Docker Image
In building the latest image specify the latest tag:
````bash
$ ./generate-build-version.sh
$ docker build -t hubmap/spatial-api:latest .
````

In building a release version of the image, use the `main` branch, and specify a version tag (without prefix `v`).
You can see the previous version tags at [DockerHub Spatial APi](https://github.com/hubmapconsortium/spatial-api/releases/).
````bash
$ ./generate-build-version.sh
$ docker build -t hubmap/spatial-api:1.0.0 .
````

### Publish the Image to DockerHub
Saving the image requires access to the DockerHub account with 'PERMISSION' 'Owner' account.
You may also see [DockerHub Spatial APi](https://github.com/hubmapconsortium/spatial-api/releases/).
To make changes you must login.
````bash
$ docker login
````

For DEV/TEST/STAGE, just use the `latest` tag.
````bash
$ docker push hubmap/spatial-api:latest
````

For PROD, push the released version/tag that you have built above.
````bash
$ docker push hubmap/spatial-api:1.0.0
````

### PROD Documenting the Docker image

Reelase workflow:
- merge code to the release branch (typically 'main') in github
- bump the version number in ./VERSION
- create a new github release and tag
- publish a new image with new tag to DockerHub
- SSH into the PROD VM and pull the new image to redeploy

#### Bump the number in ./VERSION

The version found in the Released Version that you will create below must
match that of the ./VERSION file.
Change this file before building the Docker image that you will push to Docker HUB.
The version will show up on [VERSION](https://github.com/hubmapconsortium/spatial-api/blob/main/VERSION).


#### Create a new Github Release Tag

For PROD, after you've created the numbered release you should save it in
the project [Release](https://github.com/hubmapconsortium/spatial-api/releases/) page.
On this page, click on the `Draft a new release` (white on black) button, or if there are no releases
click on the `Create a new release` (white on green) button.
Click on the `Choose a tag` button, enter the tag name, and then `+ Create new tag: v.?.?.? on publish` (with prefix `v`).
The new tag will appear in place of the text on the `Choose a tag` button.
Create a new release version in the `Release title` box.
Use the same release number as was used in DockerHub, but prefix it with the letter v (see `Tag suggestion` on the left),
and enter release notes in the `Write` section.
Then click on the `Publish release` (white on green) button.

### Deploy the Saved Image
For PROD, download the new numbered release image from DockerHub to the deployment server in the Git repository
directory. If you build the image on the deployment server you can skip this step as it should already be on the server.
You can use `docker images` to confirm this.
````bash
$ docker pull hubmap/spatial-api:1.0.0
````

For DEV, you can use `latest` take rather than the `1.0.0` tag above, or what ever the current tag is in the file ./VERSION.

Determine the current image version. This will show you which Docker image the process is running under.
If the process has stopped for some reason you should try `docker images`.
````bash
$ docker ps
CONTAINER ID        IMAGE                       COMMAND                  CREATED             STATUS                  PORTS                          NAMES
407cbcc4d15d        hubmap/spatial-api:1.0.0    "/usr/local/bin/entr…"   3 weeks ago         Up 3 weeks (healthy)    0.0.0.0:5000->5000/tcp         spatial-api
...
````
Stop the process associated with container (Docker image), delete it. Then build and deploy it.
````bash
$ ssh -i ~/.ssh/id_rsa_e2c.pem cpk36@18.205.215.12
$ sudo /bin/su - hive
$ cd /opt/hubmap/spatial-api
$ git checkout main
$ git pull
$ export SPATIAL_API_VERSION=1.0.0; docker-compose -f docker-compose.api.deployment.yml down --rmi all
$ export SPATIAL_API_VERSION=1.0.0; docker-compose -f docker-compose.api.deployment.yml up -d --no-build
$ docker ps
CONTAINER ID   IMAGE                     COMMAND                  CREATED          STATUS           PORTS                                        NAMES
aa0b6676c615   spatial-api_spatial_db    "docker-entrypoint.s…"   28 seconds ago   Up 28 seconds    0.0.0.0:5432->5432/tcp, :::5432->5432/tcp    spatial_db
````

The production version of the server should be running at...
````bash
https://spatial.api.hubmapconsortium.org/
````

### Examine Server Logs
To look at the logs of the running server, you may use.
```bash
$ tail -f server/log/uwsgi-spatial-api.log
```

## Local Deployment

Before deploying the server you will need to configure it.
Please follow the steps outlined in the section `Configuration File`.
For the spatial-api to access the PostgreSQL server in the container you will
want to use...
```bash
[postgresql]
  Server = db:5432
  Db = spatial
  Username = spatial
```

Then you can restore the Docker Containers, Networks, and Volumes by executing the following script.
If you delete one of the Docker images (say the `spatial-api_web-1` container) this will rebuild and restart it.
With the indicated optional parameters `-dlt` it will also delete and rebuild the containers, reload the data, and run the tests.
```bash
$ ./scripts/run_local.sh -dlt
```

You will not need to create the tables on the PostgreSQL database that is running in the container
as this is done when the database starts up as it by default reads the file `db/initdb.d/initdb.sql`.


# Adding New Endpoints

An endpoint should be created in a Python module using Blueprint with its name (e.g., `server/spatialapi/routes/new_endpoint/__init__.py`).
It should then be registered in the `server/__init__.py` file.

## OpenAPI Spec

The endpoints should be documented using [OpenAPI v3](https://swagger.io/specification/).
The specification .yml file should be found at the top lever of the project, and named `spatial-api-spec.yml`

### SmartAPI

All of the HubMAP APIs are found [here](https://smart-api.info/registry?q=hubmap).

The Spatial API is found [here](https://smart-api.info/ui/f81c4c1977642e0a9c8adbf0486cad40),
and is reloaded from the file `spatial-api-spec.yaml` in the `main` branch sometime after midnight Eastern Time US.
It contains only the search related endpoints.

The other administrative endpoints are found in `spatial-api-spec-private.yaml`.

### Registering Endpoints
All endpoints should be registered in the `AWS API Gateway`.
Currently this is a manual process.

The urls are as follows:
[DEV](https://spatial-api.dev.hubmapconsortium.org/),
[TEST](https://spatial-api.test.hubmapconsortium.org/),
[STAGE](https://spatial-api.stage.hubmapconsortium.org/),
[PROD](https://spatial.api.hubmapconsortium.org/).

## Method Verification Data

It was important to verify that the manner in which we are loading spatial data into the `sample` table produces
the results that we were expecting.
In order to do this "well behaved" data was constructed in the `geom_test` table.
Several 10x10x10 cubes were created and spaced at different intervals by a `Translate` operation.
The `db/run_test.sql` file contains a comment which represents the distance between the origin `POINTZ(0 0 0)`
and a radius (computed using the Pythagorean theorem). A pair of queries are used for each cube.
The first query uses a radius which is just a tiny bit shy of the radius that the cube should be found.
The second query uses a radius which is just at the radius where the Pythagorean theorem says that the cube should be found.

Here are the first two queries of the test script which illustrates this.
```bash
$ ./scripts/run_test.sh
Running test queries...
Password for user spatial: 
-- sqrt(10^2 + 10^2 + 10^2) = 17.321
SELECT id FROM geom_test
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 17.32);
 id 
----
(0 rows)

SELECT id FROM geom_test
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 17.321);
 id 
----
  1
(1 row)
```
The first query shows that closest cube to the origin (created in `db/initdb.d/initdb.sql`) is not found
at radius `17.320`, but is found at radius `17.321` which is where the Pythagorean theorem (in comment)
```bash
-- sqrt(10^2 + 10^2 + 10^2) = 17.321
```
says that it should be found.

This cube corresponds to the first cube created in the `db/initdb.d/iniddb.sql` file.
```bash
INSERT INTO geom_test (geom)
  VALUES (ST_Translate(ST_MakeSolid('POLYHEDRALSURFACE Z(
        ((-5.0 -5.0 5.0, 5.0 -5.0 5.0, 5.0 5.0 5.0, -5.0 5.0 5.0, -5.0 -5.0 5.0)),
        ((-5.0 -5.0 -5.0, -5.0 5.0 -5.0, 5.0 5.0 -5.0, 5.0 -5.0 -5.0, -5.0 -5.0 -5.0)),
        ((-5.0 -5.0 -5.0, -5.0 -5.0 5.0, -5.0 5.0 5.0, -5.0 5.0 -5.0, -5.0 -5.0 -5.0)),
        ((5.0 -5.0 -5.0, 5.0 5.0 -5.0, 5.0 5.0 5.0, 5.0 -5.0 5.0, 5.0 -5.0 -5.0)),
        ((-5.0 5.0 -5.0, -5.0 5.0 5.0, 5.0 5.0 5.0, 5.0 5.0 -5.0, -5.0 5.0 -5.0)),
        ((-5.0 -5.0 -5.0, 5.0 -5.0 -5.0, 5.0 -5.0 5.0, -5.0 -5.0 5.0, -5.0 -5.0 -5.0)) )'),
         15, 15, 15));
```

This cube is constructed as a Polyhedral Surface which is a 3D figure made exclusively of six (6) Polygons.
It is a contiguous collection of polygons, which share common boundary segments.
In our case the surfaces of the polygons are all `outside` surfaces.
An `outside` surface is a polygon that has a `winding order` of counterclockwise,
that is the points are specified in a counter clockwise manner.
An `inside` suface is a polygon that has a `winding order` of clockwise.

You can run tests on the geometric objects that are in the database by running
`geom.py` with an option of `-c`. It checks to make sure that all of the geometries
are `closed`, `solids`, and have the `correct volume`.
````bash
$ (cd server; export PYTHONPATH=.; python3 ./tests/geom.py -c -C $CONFIG)
````

If you wish to see what a 3D Polyhedral Surface of a given length, width,
and height looks like you can use `spatial_manager.py` with the `-p` option.
Here a Polyhedral Surface is created with a length of 23, a width of 14, and a height of 9.
````bash
(cd server; export PYTHONPATH=.; python3 ./spatialapi/manager/spatial_manager.py -p '23 14 9')
[2022-06-30 16:57:04] INFO in spatial_manager:334: Dimensions given are x: 23.0, y: 14.0, z: 9.0
'POLYHEDRALSURFACE Z(((-11.5 -7.0 4.5, 11.5 -7.0 4.5, 11.5 7.0 4.5, -11.5 7.0 4.5, -11.5 -7.0 4.5)),((-11.5 -7.0 -4.5, -11.5 7.0 -4.5, 11.5 7.0 -4.5, 11.5 -7.0 -4.5, -11.5 -7.0 -4.5)),((-11.5 -7.0 -4.5, -11.5 -7.0 4.5, -11.5 7.0 4.5, -11.5 7.0 -4.5, -11.5 -7.0 -4.5)),((11.5 -7.0 -4.5, 11.5 7.0 -4.5, 11.5 7.0 4.5, 11.5 -7.0 4.5, 11.5 -7.0 -4.5)),((-11.5 7.0 -4.5, -11.5 7.0 4.5, 11.5 7.0 4.5, 11.5 7.0 -4.5, -11.5 7.0 -4.5)),((-11.5 -7.0 -4.5, 11.5 -7.0 -4.5, 11.5 -7.0 4.5, -11.5 -7.0 4.5, -11.5 -7.0 -4.5)) )'
````
It will create a Polyhedral Surface with it's center at the origin.
You can then use `translation` and `rotation` to further place it in the space.

## Deploy Database

The following will allow you to connect to the database host, destroy the database and rebuild the table structure and stored procedures...
````bash
$ ssh -i ~/.ssh/id_rsa_e2c.pem cpk36@18.205.215.12
$ sudo /bin/su - hive
$ cd /opt/hubmap/spatial-api
$ git checkout main
$ git pull
$ docker-compose -f docker-compose.db.deployment.yml down --rmi all
$ docker-compose -f docker-compose.db.deployment.yml up --build -d
$ docker ps
CONTAINER ID   IMAGE                     COMMAND                  CREATED          STATUS           PORTS                                        NAMES
aa0b6676c615   spatial-api_spatial_db    "docker-entrypoint.s…"   28 seconds ago   Up 28 seconds    0.0.0.0:5432->5432/tcp, :::5432->5432/tcp    spatial_db
````

The following script will allow you to load data into the database.
It will access the spatial-api server and execute several endpoints
that will allow for the rebuilding of the: annotation details,
organ-sample-data (RK & LK), and the cell type counts.

To get the BEARER_TOKEN using Firefox open a "New Private Window".
Then access the Developer Tool (Tools > Browser Tools > Web Developer Tools).
Login through the [UI](https://portal.hubmapconsortium.org/).
Examine the Request Header > Authorization, of the search-api calls.
The very long string following the text BEARER <sp> is what you want.
After you copy that string close the web browser.
````bash
$ ./scripts/db_rebuild.sh -H https://spatial-api.dev.hubmapconsortium.org -t BEARER_TOKEN
````

## Deploy Server

Connect to the server host, destroy the old image, build and redeploy.
````bash
$ ssh -i ~/.ssh/id_rsa_e2c.pem cpk36@ingest.dev.hubmapconsortium.org
$ sudo /bin/su - hive
$ cd /opt/hubmap/spatial-api
$ git checkout main
$ git pull
$ export SPATIAL_API_VERSION=latest; docker-compose -f docker-compose.api.deployment.yml down --rmi all
$ docker build -t hubmap/spatial-api:latest .
$ docker push hubmap/spatial-api:latest
$ export SPATIAL_API_VERSION=latest; docker-compose -f docker-compose.api.deployment.yml up --no-build -d
$ docker ps
CONTAINER ID   IMAGE                     COMMAND                  CREATED         STATUS                           PORTS     NAMES
b747d2cfd62f   hubmap/spatial-api:latest "/usr/local/bin/entr…"   4 seconds ago   Up 3 seconds (health: starting)  5000/tcp
````

If deploying other than the `latest` version for test you should give the appropriate version number.

### Server Tests

There are several scripts that allow you to run tests against the server.

The following will run tests against the dev server:
````bash
$ ./scripts/search_hubmap_id.sh -H https://spatial-api.dev.hubmapconsortium.org
$ ./scripts/spatial_search_hubmap_id.sh -H https://spatial-api.dev.hubmapconsortium.org
$ ./scripts/point_search.sh -H https://spatial-api.dev.hubmapconsortium.org
````
By default the tests run agains `http://localhost:5001`
````bash
$ ./scripts/search_hubmap_id.sh
$ ./scripts/spatial_search_hubmap_id.sh 
$ ./scripts/point_search.sh
````
