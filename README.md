# translation_api
the world on the same page

## Setup
1. Clone the repository
2. run `docker-compose up --build`
3. run `docker-compose exec flask_api flask db init`
4. run `docker-compose exec flask_api flask db migrate`
5. run `docker-compose exec flask_api flask db upgrade`
have fun

***
(If you have errors with auth on postgres make sure the local version is not interfering with the docker container version)

TODO:
    - Test other flask routes
    - remove kafka if its not needed
    - remove zookeeper if its not needed
    - test messaging and the llm service
    - consider some tool like swagger to document the api
    - consider some tool like pytest to test the api
    - consider some tool to view the containers status, availablitiy, logs, etc
    
