# initdb.d

The official postgres docker image will run .sql scripts found in the /docker-entrypoint-initdb.d/ folder.

In the docker-compose file:
```commandline
services:
  db:
    volumes:
      - # The official postgres docker image will run .sql scripts found in the /docker-entrypoint-initdb.d/ folder.
      - ./db/initdb.d:/docker-entrypoint-initdb.d/
```