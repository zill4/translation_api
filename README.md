# translation_api
the world on the same page
## Setup
1. Clone the repository
2. Run the setup script:
    poetry install
3. Create a `.env` file with the following variables:
    FLASK_APP=main.py
    FLASK_ENV=development
    FLASK_DEBUG=1
    SQLALCHEMY_DATABASE_URI=postgresql://username:password@localhost:5432/database_name
    JWT_SECRET_KEY=your_secret_key
    JWT_ACCESS_TOKEN_EXPIRES=3600
    JWT_REFRESH_TOKEN_EXPIRES=86400
    (Make sure to change the database_name, username, and password to your own)
4. Run Docker Compose to start the database:
    docker-compose up -d
    (To shutdown the database, run `docker-compose down`)
5. Run
    poetry run python3 main.py

***
To connect to the database via Docker.
`docker exec -it translation_api-db-1  psql -U jcrisp -d ai_service_db`
(If you have errors with auth on postgres make sure the local version is not interfering with the docker container version)