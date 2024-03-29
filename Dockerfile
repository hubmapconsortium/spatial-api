FROM python:3.9.5-alpine

RUN apk add --no-cache --update build-base gcc libc-dev libffi-dev linux-headers pcre-dev postgresql-dev postgresql-libs su-exec curl

ENV VIRTUAL_ENV=/app
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN python3 -m pip install --upgrade pip

WORKDIR /app
COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /app/server
COPY server/spatialapi spatialapi
#ENV PYTHONPATH="${PYTHONPATH}:/app/server"
COPY server/uwsgi.ini .
COPY server/wsgi.py .

# The EXPOSE instruction informs Docker that the container listens on the specified network ports at runtime.
# EXPOSE does not make the ports of the container accessible to the hos
EXPOSE 5000

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT [ "/usr/local/bin/entrypoint.sh" ]

# Finally, we run uWSGI with the ini file
CMD [ "uwsgi", "--ini", "/app/server/uwsgi.ini" ]
