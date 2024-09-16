useful commands for migrating the database
   docker-compose exec flask_api flask db init
   docker-compose exec flask_api flask db migrate
   docker-compose exec flask_api flask db upgrade
