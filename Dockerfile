FROM amazon/aws-lambda-python:3.11 AS build

COPY Pipfile* /var/task
COPY *.py /var/task
COPY actionnetwork_activist_sync /var/task/actionnetwork_activist_sync

RUN yum install -y zip
RUN pip install pipenv
RUN pipenv requirements > requirements-lock.txt
RUN pip install -r requirements-lock.txt -t .
RUN find . -name __pycache__ | xargs rm -rf
RUN mkdir dist
RUN zip -9r dist/sync.zip .

FROM scratch
COPY --from=build /var/task/dist /
