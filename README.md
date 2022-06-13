# spatial-api

This information will help you get the Spatian API up in running whether locally or on an environment.

## Configuration File

The configuration file should be located in `resources/app.properties` for deployment.
There is a `resources/app.example.properties` that you can use as a template for `resources/app.properties`.
The `resources/application.example.properties` assumes that the database is running in
a docker container with a network common to the Spatial API container.
This will likely be the case when running locally (see `scripts/run_local.sh`).

The `resources/app.local.properties` is used by scripts that wish to access the database
running in the local Docker containers.
The notable difference is that when accessing the PostgreSQL server form the container
(as the microservice would do) the database Services name `db` (from `docker-compose.yml`) should be used.
When accessing the database from a script running on the localhost (anything in `scripts`), `localhost` should be used.

Since this microservice accesses a Neo4j, and a PosgreSQL database you will need to provide the server,
user, and password for these.

The `resources/app.properties` should never be saved to GitHUB as it contains passwords.
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
$ sudo /bin/su - centos
$ cd hubmap/spatial-api
$ pwd
/home/centos/hubmap/spatial-api
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
$ docker build -t hubmap/spatial-api:latest .
````

In building a release version of the image, use the `main` branch, and specify a version tag (without prefix `v`).
You can see the previous version tags at [DockerHub Spatial APi](https://github.com/hubmapconsortium/spatial-api/releases/).
````bash
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

For DEV, you can use `latest` take rather than the `1.0.0` tag above.

Determine the current image version. This will show you which Docker image the process is running under.
If the process has stopped for some reason you should try `docker images`.
````bash
$ docker ps
CONTAINER ID        IMAGE                       COMMAND                  CREATED             STATUS                  PORTS                          NAMES
407cbcc4d15d        hubmap/spatial-api:1.0.0    "/usr/local/bin/entr…"   3 weeks ago         Up 3 weeks (healthy)    0.0.0.0:5000->5000/tcp         spatial-api
...
````
Stop the process associated with container (Docker image) and delete it.
````bash
$ export SPATIAL_API_VERSION=1.0.0; docker-compose -f docker-compose.deployment.yml down --rmi all
````
Start the new container using the image just pulled from DockerHub.
````bash
$ export SPATIAL_API_VERSION=1.0.0; docker-compose -f docker-compose.deployment.yml up -d --no-build
````

Make sure that the new images has started.
````bash
$ docker ps
CONTAINER ID        IMAGE                       COMMAND                  CREATED             STATUS                            PORTS                       NAMES
5c0bdb68bd22        hubmap/spatial-api:1.0.0    "/usr/local/bin/entr…"   6 seconds ago       Up 4 seconds (health: starting)   0.0.0.0:5000->5000/tcp      spatial-api
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


# Adding new endpoints

An endpoint should be created in a Python module with its name (e.g., `server/spatialapi/new_endpoint/__init__.py`).
It should then be registered in the `server/__init__.py` file.

## OpenAPI Spec

The endpoints should be documented using [OpenAPI v3](https://swagger.io/specification/).
The specification .yml file should be found at the top lever of the project, and named `spatial-api-spec.yml`

### SmartAPI

All of the HubMAP APIs are found [here](https://smart-api.info/registry?q=hubmap).
They are reloaded from the `master` branch specification .yml file sometime after midnight Eastern Time US.

## Method Verification Data

It was important to verify that the manner in which we are loading spatial data into the `sample` table produces
the results that we were expecting.
In order to do this "well behaved" data was constructed in the `geom_test` table.
Several 5x5x5 cubes were created and spaced at different intervals by a `Translate`.
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
SELECT id FROM "public"."geom_test"
   WHERE ST_3DDWithin(geom, ST_GeomFromText('POINTZ(0 0 0)'), 17.32);
 id 
----
(0 rows)

SELECT id FROM "public"."geom_test"
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
INSERT INTO "public"."geom_test" (geom)
  VALUES (ST_Translate(ST_GeomFromText('MULTIPOLYGON Z(
        ((-5 -5 -5, -5 -5 5, -5 5 5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, 5 -5 -5, 5 5 -5, -5 5 -5, -5 -5 -5)),
        ((-5 -5 -5, -5 -5 5, 5 -5 5, 5 -5 -5, -5 -5 -5)),
        ((-5 5 -5, -5 5 5, 5 5 5, 5 5 -5, -5 5 -5)),
        ((-5 -5 5, -5 5 5, 5 5 5, -5 5 5, -5 -5 5)),
        ((5 -5 -5, 5 -5 5, 5 5 5, 5 5 -5, 5 -5 -5)) )'),
         15, 15, 15));
```
This is a cube of size `10x10x10` created at the default origin `POINTZ(0 0 0)`, and translated 15 in the X, Y, and Z direction.
This would place the closest point of the cube on any axis with the origin of `POINTZ(0 0 0)` at a radius of `15-5=10`.
Where `15` represents the location of the centroid (from the Translate),
and `-5=-10/2` the closest point of a `10x10x10` cube located at that centroid.
