docker stop pg-bot
docker rm pg-bot
docker rmi pg-bot
docker build -t pg-bot .
docker run -d -p 80:80 pg-bot