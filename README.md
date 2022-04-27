# spatial-api

This information will help you get the Spatian API up in running whether locally or on an environment.

## Configuration File

The configuration file should be located in `resources/app.properties` for deployment,
and `resources/app.local.properties` access by scripts that wish to access the microservice
running in the local Docker containers.
There is a `resources/app.example.properties` that you can use as a template.
The `resources/application.example.properties` assumes that the database is running in
a docker container with a network common to the Spatial API.
This will likely not be the case when not running locally.

Since this micro-service accesses a Neo4j, and a PosgreSQL database you will need to provide the server, user, and password.

The `resources/app.properties` should never be saved to GitHUB as it contains passwords.
You should create it on the deployment machine.


## Build, Publish, Deploy Workflow
These are the steps used to build, publish a Docker image, and then deploy it.

Before doing so you will need to follow the steps outlined in the section `Configuration File`
to configure the server.

Local deployment instructions for testing purposes are found in the Section `Local Deployment`.

### Get the Latest Code
Login to the deployment server (in this case DEV) and get the latest version of the code from the GitHub repository.
For production the deployment machine is `ingest.hubmapconsortium.org`.
```bash
# Access the server, switch accounts and go to the server directory
$ ssh -i ~/.ssh/id_rsa_e2c.pem cpk36@ingest.dev.hubmapconsortium.org
$ sudo /bin/su - centos
$ cd hubmap/spatial-api
$ pwd
/home/centos/hubmap/spatial-api
$ git checkout master
$ git status
# On branch master
...
$ git pull
```
For production the deployment machine is `ingest.hubmapconsortium.org`.
```bash
$ ssh -i ~/.ssh/id_rsa_e2c.pem cpk36@ingest.hubmapconsortium.org
...
```
You should now have the most recent version of the code which should be in the `master`
branch. You can also deploy other branches on DEV for testing.

### Build Docker Image
In building the latest image specify the latest tag:
````bash
$ docker build -t hubmap/spatial-api:latest .
````

In building a release version of the image, use the `master` branch, and specify a version tag.
You can see the previous version tags at [DockerHub Spatial APi](https://github.com/hubmapconsortium/spatial-api/releases/).
````bash
$ docker build -t hubmap/spatial-api:1.0.2 .
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

For PROD, push the released version/tag.
````bash
$ docker push hubmap/spatial-api:1.0.2
````

### PROD Documenting the Docker image
For PROD, after you've created the numbered release you should save it in
the project [Release](https://github.com/hubmapconsortium/spatial-api/releases) page.
On this page, click on the `Draft a new release` (white on black) button.
Click on the `Choose a tag` button, enter the tag name, and then the `+ Create new tag: on publish`.
Create a new release version in the `Release title` box.
Use the same release number as in DockerHub, but prefix it with the letter v (see `Tag suggestion` on the left),
and enter release notes in the `Write` section.
Then click on the `Publish Release` (green) button.

### Deploy the Saved Image
For PROD, download the new numbered release image from DockerHub to the deployment server in the Git repository
directory.
````bash
$ docker pull hubmap/spatial-api:1.0.2
````
For DEV, you can use `latest`.

Determine the current image version.
````bash
$ docker ps
CONTAINER ID        IMAGE                       COMMAND                  CREATED             STATUS                  PORTS                          NAMES
407cbcc4d15d        hubmap/spatial-api:1.0.1    "/usr/local/bin/entr…"   3 weeks ago         Up 3 weeks (healthy)    0.0.0.0:5000->5000/tcp         spatial-api
...
````
Stop the process associated with it and delete the image.
````bash
$ export SPATIAL_API_VERSION=1.0.1; docker-compose -f docker-compose.deployment.yml down --rmi all
````
Start the new container using the image just pulled from DockerHub.
````bash
$ export SPATIAL_API_VERSION=1.0.2; docker-compose -f docker-compose.deployment.yml up -d --no-build
````

Make sure that the new images has started.
````bash
$ docker ps
CONTAINER ID        IMAGE                       COMMAND                  CREATED             STATUS                            PORTS                       NAMES
5c0bdb68bd22        hubmap/spatial-api:1.0.2    "/usr/local/bin/entr…"   6 seconds ago       Up 4 seconds (health: starting)   0.0.0.0:5000->5000/tcp      spatial-api
````

The production version of the server should be running at...
````bash
https://spatial.hubmapconsortium.org/
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

To shutdown and remove all containers if anything is running by executing the following:
```bash
$ ./scripts/run_local.sh down -v --rmi all
```

Then restore the Docker Containers, Networks, and Volumes can be done by executing the following script.
If you delete one of the Docker images (say the `spatial-api_web-1` container) this will rebuild and restart it.
```bash
$ ./scripts/run_local.sh
```

You will not need create the tables on the PostgreSQL database that is running in the container
as this is done when the database starts up as it reads the file `db/initdb.d/initdb.sql`.

Now that the tables exist, you will need to load some data into them from Elastic Search.
You do this by running the script.
```bash
$ ./scripts/insert_organ_data_rk.sh
```

Once the data is loaded you can conduct some searches using
```bash
$ ./scripts/search_hubmap_id.sh
```
