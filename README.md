# Amino Bot

This Python-based Amino Bot is designed to enhance your Amino community experience with features like anti-raid, anti-lag profiles, admin commands, and warnings. This README provides instructions on how to set up and run the bot.

## Usage

1. Clone the repository to your local machine:

```bash
git clone https://github.com/Dmitry-Kang/amino_comm_bot.git
cd amino_comm_bot
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Run the bot:

```bash
python3 main.py
```

## Configuration

Before running the bot, make sure to edit the `.env` file with your Amino credentials and any other configuration settings.

```bash
EMAIL=your email
PASSWORD=your password
COMMUNITY_ID=community id
```

- `EMAIL`: Your Amino email address.
- `PASSWORD`: Your Amino account password.
- `COMMUNITY_ID`: The ID of the Amino community.

## Deploying on Heroku

If you wish to deploy the bot on Heroku, a `Procfile` is included in the repository. Follow these steps:

1. Create a Heroku account if you don't have one.
2. Install the Heroku CLI.
3. Login to Heroku using `heroku login`.
4. Create a new Heroku app: `heroku create your-amino-bot-name`.
5. Push the code to Heroku: `git push heroku master`.

Make sure to set your Amino credentials and other configuration settings as environment variables on the Heroku dashboard.

## Bot Commands

- Admin commands (specific roles required):
  - `mute 1`: Mutes a user from the community, 1 - 1 hour, 2 - 3 hours, 3 - 6 hours, 4 - 12 hours, 5 - 24 hours.
  - `ban`: Ban a user from the community.
  - `get antiban`: List users who have a lot of heavy characters in their profile.

Feel free to customize and extend the bot to suit your community's needs. Happy botting!
