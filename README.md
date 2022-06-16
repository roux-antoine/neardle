# Neardle: a nerdy version of Heardle

## What is this

A Spotify-based command line music blind test game, based on [Heardle](https://www.heardle.app) but with options to get nerdier.

It offers multiple ways to generate the database of songs to guess: artists, genres or existing playlists. It is meant to be played by one or multiple players, on a single device.

## How to setup

0. Pre-requisites
    - `Python 3` installed on the device
    - A non-free Spotify account
1. Clone this repo
2. Install the required Python libraries
    - (Recommended) Create a Python virtual environment and activate it (see [this link](https://docs.python.org/3/library/venv.html))
    - Run `pip install -r requirements.txt`
3. Create a Spotify app
    - Open the dashboard in Spotify Developers (see [this link](https://developer.spotify.com/dashboard/))
    - Click "Create an app", give it a name etc
    - Make a note of the `Client ID` and `Client Secret`
4. Create a `credentials.py` file
    - In the repo, copy the file `credentials_template.py` into a file called `credentials.py`
    - Replace the `TODO`s by your `Client ID` and `Client Secret`


## How to play

1. Run `python main.py`
2. The app will prompt you to login to Spotify. Do so and enter the URL that you have been redirected too
3. Enter the player name(s)
4. Follow the prompts to select how to generate the database of songs
5. Wait until the database of songs has been generated (may take a few minutes)
6. Open Spotify on a device (can be different to the device where Neardle is running) and play a bit of music to make this device the active device
7. Press the `Enter` key to start playing
