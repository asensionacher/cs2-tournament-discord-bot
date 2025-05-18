FROM gorialis/discord.py:3.9-alpine-extras

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Run the bot on container start
CMD [ "python", "./src/main.py" ]