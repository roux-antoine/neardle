import copy
import inquirer
import os
import random
import spotipy
import time

from difflib import SequenceMatcher

import params
import credentials
import utils


class Track:
    def __init__(self, artist, album, name, uri, popularity):
        """Constructor for Track

        Args:
            artist (Artist): artist of the track.
            album (Album): album the track is part of.
            name (str): name of the track.
            uri (str): Spotify uri of the track.
            popularity (int): Spotify popularity of the track.
        """
        self.artist = artist
        self.album = album
        self.name = name
        self.uri = uri
        self.popularity = popularity
        self.legible_name = f"{self.artist} -- {self.name}"

    def get_details(self):
        """Returns a string with details about the track

        Returns:
            str: details about the track
        """
        return f"{self.legible_name} ({self.album.name} -- {self.album.year_released}) ({self.popularity})"

    def __repr__(self):
        return self.legible_name


class Artist:
    def __init__(self, name, uri):
        """Constructor for Artist

        Args:
            name (str): name of the artist.
            uri (str): Spotify uri of the artist.
        """
        self.name = name
        self.uri = uri

    def __repr__(self):
        return self.name


class Album:
    def __init__(self, name, artist, year_released, uri):
        """Constructor for Album

        Args:
            name (str): name of the album.
            artist (Arist): artist of the album.
            year_released (str): year the album was released according to Spotify.
            uri (str): Spotify uri of the album.
        """
        self.name = name
        self.artist = artist
        self.year_released = year_released
        self.uri = uri


class Stats:
    def __init__(self):
        """Constructor for Stats"""
        self.stages_durations = {nb_second: 0 for nb_second in params.STAGES_DURATION}
        self.correct_release_years = 0
        self.close_release_years = 0
        self.incorrect_release_years = 0
        self.correct_albums = 0
        self.incorrect_albums = 0

    def __repr__(self):
        output = "Stages durations:\n"
        for stage_duration, number in self.stages_durations.items():
            output += f"  {stage_duration:2} seconds: {number:2} times\n"
        output += f"Release years correctly guessed: {self.correct_release_years}\n"
        output += f"Release years closely guessed: {self.close_release_years}\n"
        output += f"Release years incorrectly guessed: {self.incorrect_release_years}\n"
        output += f"Albums correctly guessed: {self.correct_albums}\n"
        output += f"Albums incorrectly guessed: {self.incorrect_albums}\n"

        return output


class Player:
    def __init__(self, name):
        """Constructor for Player

        Args:
            name (str): name of the player.
        """
        self.name = name
        self.score = 0
        self.stats = Stats()

    def __repr__(self):
        return f"{self.name} ({self.score} points)"


class Game:
    def __init__(self):
        """Constructor for Game"""
        players_names_input = input(
            "Enter the names of players as a comma-separated list: "
        )
        self.players_names = [name.strip() for name in players_names_input.split(",")]
        self.players_dict = {name: Player(name) for name in self.players_names}

        self.sp = spotipy.Spotify(
            auth_manager=spotipy.oauth2.SpotifyOAuth(
                client_id=credentials.CLIENT_ID,
                client_secret=credentials.CLIENT_SECRET,
                redirect_uri="http://example.com",
                scope="user-library-read user-read-currently-playing user-read-playback-state user-modify-playback-state",
            )
        )

        self.tracks_db = []
        self.artists_db = []

    def get_top_N_tracks_from_artist(self, artist):
        """Gets the top 10 (or less) tracks of an artist according to Spotify

        We filter tracks which name is not too close to a track already considered

        Args:
            artist (Artist): the artist to find the popular tracks of.

        Returns:
            List[Track]: list of N most popular Tracks from the artist
        """
        results = self.sp.artist_top_tracks(artist.uri)
        top_n_tracks = []
        for track in results["tracks"]:
            if not utils.name_is_similar_to_existing(track["name"], top_n_tracks):
                album = Album(
                    track["album"]["name"],
                    artist,
                    track["album"]["release_date"][:4],
                    track["album"]["uri"],
                )
                top_n_tracks.append(
                    Track(
                        artist, album, track["name"], track["uri"], track["popularity"]
                    )
                )
        return top_n_tracks

    def get_artist_uri(self, artist_query):
        """Gets the uri of the artist passed as query

        Args:
            artist_query (str): The name of the artist to query for.

        Returns:
            str: the uri of the artist if found, None otherwise
        """
        results = self.sp.search(q=f"artist: {artist_query}", type="artist")
        items = results["artists"]["items"]
        if len(items) > 0:
            return items[0]["uri"]
        else:
            print(f"{artist_query} not found")
            return None

    def get_all_popular_tracks_from_artist(
        self, artist, dateframe_start, dateframe_end
    ):
        """Get the list of popular Tracks from the artist

        There is some pretty heavy filtering of the tracks found:
        - making sure that the main artist of the track is the artist of interest
        - keeping only tracks which are more popular than the general threshold
        - keeping only tracks which name is not too close to a track already considered

        Args:
            artist (Artist): the artist to find the popular tracks of.
            dateframe_start (str): start year of the date frame
            dateframe_end (str): end year of the date frame

        Returns:
            List[Track]: list of popular Tracks from the artist
        """
        offset = 0
        raw_tracks = []

        # Step 1: we get all tracks from the artist
        while offset < params.MAX_OFFSET:
            results = self.sp.search(
                q=f"artist: {artist.name}",
                limit=params.PAGE_SIZE,
                type="track",
                offset=offset,
            )["tracks"]

            offset += params.PAGE_SIZE

            for track in results["items"]:
                if artist.name != track["album"]["artists"][0]["name"]:
                    # it means the track does not come from the artist of interest
                    continue
                if utils.date_in_dateframe(
                    track["album"]["release_date"], dateframe_start, dateframe_end
                ):
                    album = Album(
                        track["album"]["name"],
                        artist,
                        track["album"]["release_date"][:4],
                        track["album"]["uri"],
                    )
                    raw_tracks.append(
                        Track(
                            artist,
                            album,
                            track["name"],
                            track["uri"],
                            track["popularity"],
                        )
                    )

            if not results["next"]:
                break

        # Step 2: we keep only the tracks which are popular enough
        popular_tracks = [
            track
            for track in raw_tracks
            if track.popularity > params.TRACK_POPULARITY_THRESHOLD
        ]

        # Step 3: we remove tracks that have names too close
        sorted_tracks = sorted(popular_tracks, key=lambda x: x.popularity)[::-1]
        filtered_tracks = []
        for track in sorted_tracks:
            if not utils.name_is_similar_to_existing(track.name, filtered_tracks):
                filtered_tracks.append(track)

        # Step 4: we keep only the max N tracks out of this
        filtered_tracks = filtered_tracks[: params.MAX_TRACKS_PER_ARTIST]

        return filtered_tracks

    def get_related_artists(self, artist):
        """Get artists related to the artist of interest according to Spotify

        Args:
            artist (Artist): the artist to find the related artists of.

        Returns:
            List[Artist]: The related artists.
        """

        names_artists_already_in_db = set([artist.name for artist in self.artists_db])
        results = self.sp.artist_related_artists(artist.uri)["artists"]
        related_artists = []
        for result in results:
            if (
                result["name"] not in names_artists_already_in_db
                and result["popularity"] > params.ARTIST_POPULARITY_THRESHOLD
            ):
                related_artists.append(Artist(result["name"], result["uri"]))
                if len(related_artists) >= params.MAX_NUMBER_RELATED_ARTISTS:
                    break

        return related_artists

    def get_tracks_in_genre(self, genre_query, dateframe_start, dateframe_end):
        """Get the list of popular Tracks in the genre

        There is some pretty heavy filtering of the tracks found:
        - keeping only tracks which are more popular than the general threshold
        - keeping only tracks which name is not too close to a track already considered

        Args:
            genre_query (str): genre to query for.
            dateframe_start (str): start year of the date frame
            dateframe_end (str): end year of the date frame

        Returns:
            List[Track]: list of tracks in the genre.
        """
        names_tracks_already_in_db = set([track.name for track in self.tracks_db])
        tracks_from_genre = []
        offset = 0

        while offset < params.MAX_OFFSET:
            results = self.sp.search(
                q=f"genre: {genre_query}",
                limit=params.PAGE_SIZE,
                type="track",
                offset=offset,
            )["tracks"]

            offset += params.PAGE_SIZE

            for track in results["items"]:
                if utils.name_is_similar_to_existing(track["name"], tracks_from_genre):
                    continue

                if (
                    track["name"] not in names_tracks_already_in_db
                    and track["popularity"] > params.TRACK_POPULARITY_THRESHOLD
                ):
                    if utils.date_in_dateframe(
                        track["album"]["release_date"], dateframe_start, dateframe_end
                    ):
                        current_artist = Artist(
                            track["artists"][0]["name"], track["artists"][0]["uri"]
                        )
                        current_album = Album(
                            track["album"]["name"],
                            current_artist,
                            track["album"]["release_date"][:4],
                            track["album"]["uri"],
                        )
                        tracks_from_genre.append(
                            Track(
                                current_artist,
                                current_album,
                                track["name"],
                                track["uri"],
                                track["popularity"],
                            )
                        )

            if not results["next"]:
                break

        return tracks_from_genre

    def get_tracks_in_user_playlist(self, playlist_query):
        """Gets the tracks in the user's playlist

        Args:
            playlist_query (str): playlist to query for.

        Returns:
            List[Track]: list of tracks in the playlist.
        """
        tracks_found = []
        results = self.sp.current_user_playlists()
        for item in results["items"]:
            if SequenceMatcher(None, item["name"], playlist_query).ratio() > 0.9:
                results = self.sp.playlist_items(item["id"])
                for item in results["items"]:
                    track = item["track"]
                    current_artist = Artist(
                        track["artists"][0]["name"], track["artists"][0]["uri"]
                    )
                    current_album = Album(
                        track["album"]["name"],
                        current_artist,
                        track["album"]["release_date"][:4],
                        track["album"]["uri"],
                    )

                    tracks_found.append(
                        Track(
                            current_artist,
                            current_album,
                            item["track"]["name"],
                            item["track"]["uri"],
                            item["track"]["popularity"],
                        )
                    )
                while results["next"]:
                    results = self.sp.next(results)
                    for item in results["items"]:
                        track = item["track"]
                        current_artist = Artist(
                            track["artists"][0]["name"], track["artists"][0]["uri"]
                        )
                        current_album = Album(
                            track["album"]["name"],
                            current_artist,
                            track["album"]["release_date"][:4],
                            track["album"]["uri"],
                        )

                        tracks_found.append(
                            Track(
                                current_artist,
                                current_album,
                                item["track"]["name"],
                                item["track"]["uri"],
                                item["track"]["popularity"],
                            )
                        )

                return tracks_found

    def get_tracks_in_public_playlist(self, playlist_query):
        """Gets the tracks in a public playlist

        Args:
            playlist_query (str): playlist to query for.

        Returns:
            List[Track]: list of tracks in the playlist.
        """
        tracks_found = []

        results = self.sp.search(q=playlist_query, type="playlist")["playlists"]

        for item in results["items"]:
            if SequenceMatcher(None, item["name"], playlist_query).ratio() > 0.9:
                results = self.sp.playlist_items(item["id"])

                for item in results["items"]:
                    track = item["track"]
                    current_artist = Artist(
                        track["artists"][0]["name"], track["artists"][0]["uri"]
                    )
                    current_album = Album(
                        track["album"]["name"],
                        current_artist,
                        track["album"]["release_date"][:4],
                        track["album"]["uri"],
                    )

                    tracks_found.append(
                        Track(
                            current_artist,
                            current_album,
                            item["track"]["name"],
                            item["track"]["uri"],
                            item["track"]["popularity"],
                        )
                    )
                while results["next"]:
                    results = self.sp.next(results)
                    for item in results["items"]:
                        track = item["track"]
                        current_artist = Artist(
                            track["artists"][0]["name"], track["artists"][0]["uri"]
                        )
                        current_album = Album(
                            track["album"]["name"],
                            current_artist,
                            track["album"]["release_date"][:4],
                            track["album"]["uri"],
                        )

                        tracks_found.append(
                            Track(
                                current_artist,
                                current_album,
                                item["track"]["name"],
                                item["track"]["uri"],
                                item["track"]["popularity"],
                            )
                        )

                return tracks_found

    def setup_tracks_database(self):
        """Sets up the database of tracks used for the blind test

        There are (for now) two ways of creating the database of tracks: artists-based or genre-based.
        For each, the user has the option to choose the top-10 tracks from Spotify or popular tracks according to out custom filtering.
        """
        question_artist_genre = [
            inquirer.List(
                "artist_genre",
                message="Play with artists or with genres?",
                choices=["Artists", "Genres", "User playlists", "Public playlists"],
            )
        ]
        answer_artist_genre = inquirer.prompt(question_artist_genre)
        if answer_artist_genre["artist_genre"] == "Artists":
            list_artists_input = input("Enter a comma-separated list of artists: ")
            list_artists = [name.strip() for name in list_artists_input.split(",")]

            for artist_query in list_artists:
                self.artists_db.append(
                    Artist(artist_query, self.get_artist_uri(artist_query))
                )

            question_related_artists = [
                inquirer.Confirm(
                    "related_artists", message="Do you want to use related artists"
                )
            ]
            answer_related_artists = inquirer.prompt(question_related_artists)
            if answer_related_artists["related_artists"]:
                for artist in copy.deepcopy(self.artists_db):
                    related_artists = self.get_related_artists(artist)
                    self.artists_db.extend(related_artists)

            print(f"Playing with a database of {len(self.artists_db)} artist\n")

            question_mode = [
                inquirer.List(
                    "mode",
                    message="What mode?",
                    choices=["Top 10", "All (popular) songs"],
                )
            ]
            answer_mode = inquirer.prompt(question_mode)
            if answer_mode["mode"] == "Top 10":
                for i, artist in enumerate(self.artists_db):
                    tracks_found = self.get_top_N_tracks_from_artist(artist)
                    self.tracks_db.extend(tracks_found)
            else:
                question_time_range = [
                    inquirer.Confirm(
                        "time_range",
                        message="Do you want to use a date range for the tracks",
                        default=True,
                    )
                ]
                answer_time_range = inquirer.prompt(question_time_range)
                if answer_time_range["time_range"]:
                    time_range_input = input("Enter dates in the format 1975-1995: ")
                    dateframe_start = time_range_input.split("-")[0]
                    dateframe_end = time_range_input.split("-")[1]
                else:
                    dateframe_start = str(params.MIN_DATE_DEFAULT)
                    dateframe_end = str(params.MAX_DATE_DEFAULT)

                for i, artist in enumerate(self.artists_db):
                    print(f"Finding tracks for artist {i}")
                    tracks_found = self.get_all_popular_tracks_from_artist(
                        artist, dateframe_start, dateframe_end
                    )
                    print(f"Found {len(tracks_found)} tracks")
                    self.tracks_db.extend(tracks_found)

        elif answer_artist_genre["artist_genre"] == "Genres":
            list_genres_input = input("Enter a comma-separated list of genres: ")
            list_genres = [name.strip() for name in list_genres_input.split(",")]

            question_time_range = [
                inquirer.Confirm(
                    "time_range",
                    message="Do you want to use a date range for the tracks",
                    default=True,
                )
            ]
            answer_time_range = inquirer.prompt(question_time_range)
            if answer_time_range["time_range"]:
                time_range_input = input("Enter dates in the format 1975-1995: ")
                dateframe_start = time_range_input.split("-")[0]
                dateframe_end = time_range_input.split("-")[1]
            else:
                dateframe_start = str(params.MIN_DATE_DEFAULT)
                dateframe_end = str(params.MAX_DATE_DEFAULT)

            for i, genre in enumerate(list_genres):
                print(f"Finding tracks for genre number {i}")
                tracks_in_genre = self.get_tracks_in_genre(
                    genre, dateframe_start, dateframe_end
                )
                print(f"Found {len(tracks_in_genre)} tracks")
                self.tracks_db.extend(tracks_in_genre)

        elif answer_artist_genre["artist_genre"] == "User playlists":
            list_playlists_input = input("Enter a comma-separated list of playlists: ")
            list_playlists = [name.strip() for name in list_playlists_input.split(",")]

            for playlist in list_playlists:
                self.tracks_db.extend(self.get_tracks_in_user_playlist(playlist))

        elif answer_artist_genre["artist_genre"] == "Public playlists":
            list_playlists_input = input("Enter a comma-separated list of playlists: ")
            list_playlists = [name.strip() for name in list_playlists_input.split(",")]

            for playlist in list_playlists:
                self.tracks_db.extend(self.get_tracks_in_public_playlist(playlist))

        print(f"Playing with a database of {len(self.tracks_db)} tracks")

    def heardle_mode(self):
        """Play with Heardle mode.

        We play a random track from the database little by little. The earlier the track is found, the more poinst are earned.
        If the track is found, there is the option of guessing the year it was released for extra points.
        """
        available_track_indexes = list(range(len(self.tracks_db)))
        number_tracks_played = 0
        while len(available_track_indexes):
            number_tracks_played += 1

            print("Standings:")
            for player in self.players_dict.values():
                print(f"  {player}")
            print()

            track_index = random.choice(available_track_indexes)
            available_track_indexes.remove(track_index)
            current_track = self.tracks_db[track_index]
            stage = 0

            while stage < len(params.STAGES_DURATION):

                print(f"Playing {params.STAGES_DURATION[stage]} seconds")
                self.sp.start_playback(uris=[current_track.uri])
                time.sleep(params.STAGES_DURATION[stage])
                self.sp.pause_playback()

                user_input = input(
                    "Enter a player's name to guess, 'r' to repeat, 'n' for next, 's' to skip: "
                ).strip()

                if user_input == "r":
                    pass
                elif user_input == "n":
                    stage += 1
                elif user_input == "s":
                    os.system("clear")
                    self.sp.start_playback(uris=[current_track.uri])
                    print(f"It was: {current_track.get_details()}\n\n")
                    break
                elif user_input in self.players_names:
                    player_guess = input(f"{user_input}, make a guess: ")

                    choices = utils.matching_titles(self.tracks_db, player_guess)
                    if len(choices) == 0:
                        print("There are no tracks that match your guess, repeating")
                        pass
                    else:
                        question_title = [
                            inquirer.List(
                                "title",
                                message="Choose between the options",
                                choices=choices,
                            )
                        ]
                        answer_title = inquirer.prompt(question_title)["title"]
                        if answer_title == f"{current_track.legible_name}":
                            self.sp.start_playback(uris=[current_track.uri])
                            print(f"Correct! It was: {answer_title}\n")
                            self.players_dict[
                                user_input
                            ].score += params.POINTS_EARNED_FOR_CORRECT_GUESS[stage]
                            self.players_dict[user_input].stats.stages_durations[
                                params.STAGES_DURATION[stage]
                            ] += 1
                            print(
                                f"You earn {params.POINTS_EARNED_FOR_CORRECT_GUESS[stage]} points"
                            )

                            if params.GUESS_YEAR:
                                question_date_released = [
                                    inquirer.Confirm(
                                        "date_released",
                                        message="Do you want to guess the release date?",
                                        default=True,
                                    )
                                ]
                                answer_date_released = inquirer.prompt(
                                    question_date_released
                                )
                                if answer_date_released["date_released"]:
                                    year_input = input("Your guess for the year: ")
                                    if year_input == current_track.album.year_released:
                                        self.players_dict[
                                            user_input
                                        ].score += params.POINTS_EARNED_FOR_PERFECT_DATE
                                        self.players_dict[
                                            user_input
                                        ].stats.correct_release_years += 1
                                        print(
                                            f"Correct! You earn {params.POINTS_EARNED_FOR_PERFECT_DATE} points"
                                        )
                                    elif (
                                        abs(
                                            int(year_input)
                                            - int(current_track.album.year_released)
                                        )
                                        <= 5
                                    ):
                                        self.players_dict[
                                            user_input
                                        ].score += params.POINTS_EARNED_FOR_CLOSE_DATE
                                        self.players_dict[
                                            user_input
                                        ].stats.close_release_years += 1
                                        print(
                                            f"Almost! It was {current_track.album.year_released}. You earn {params.POINTS_EARNED_FOR_CLOSE_DATE} points"
                                        )
                                    else:
                                        self.players_dict[
                                            user_input
                                        ].score -= params.POINTS_LOST_FOR_BAD_DATE
                                        self.players_dict[
                                            user_input
                                        ].stats.incorrect_release_years += 1
                                        print(
                                            f"Incorrect! It was {current_track.album.year_released}. You loose {params.POINTS_LOST_FOR_BAD_DATE} point"
                                        )
                                    print("\n\n")
                            if params.GUESS_ALBUM:
                                question_album = [
                                    inquirer.Confirm(
                                        "album",
                                        message="Do you want to guess the album?",
                                        default=True,
                                    )
                                ]
                                answer_album = inquirer.prompt(question_album)
                                if answer_album["album"]:
                                    album_input = input("Your guess for the album: ")
                                    if (
                                        SequenceMatcher(
                                            None, album_input, current_track.album.name
                                        ).ratio()
                                        > 0.9
                                    ):
                                        self.players_dict[
                                            user_input
                                        ].score += (
                                            params.POINTS_EARNED_FOR_CORRECT_ALBUM
                                        )
                                        self.players_dict[
                                            user_input
                                        ].stats.correct_albums += 1
                                        print(
                                            f"Correct! You earn {params.POINTS_EARNED_FOR_CORRECT_ALBUM} points"
                                        )
                                    else:
                                        self.players_dict[
                                            user_input
                                        ].score -= (
                                            params.POINTS_EARNED_FOR_INCORRECT_ALBUM
                                        )
                                        self.players_dict[
                                            user_input
                                        ].stats.incorrect_albums += 1
                                        print(
                                            f"Incorrect! It was {current_track.album.name}. You loose {params.POINTS_EARNED_FOR_INCORRECT_ALBUM} point"
                                        )
                                    print("\n\n")
                            break
                        else:
                            print(
                                f"Incorrect! You loose {params.POINTS_LOST_FOR_INCORRECT_GUESS} points"
                            )
                            self.players_dict[
                                user_input
                            ].score -= params.POINTS_LOST_FOR_INCORRECT_GUESS
                            stage += 1
                else:
                    print("Incorrect input, repeating")
                    pass

                if stage == len(params.STAGES_DURATION):
                    self.sp.start_playback(uris=[current_track.uri])
                    print(
                        f"You haven't found in time, it was: was: {current_track.get_details()}\n\n"
                    )
                    break

            if len(available_track_indexes) == 0:
                print("No more tracks to play, exiting")
            else:
                question_keep_playing = [
                    inquirer.Confirm(
                        "keep_playing",
                        message="Do you want to keep playing",
                        default=True,
                    )
                ]
                answer_keep_playing = inquirer.prompt(question_keep_playing)[
                    "keep_playing"
                ]

                if answer_keep_playing:
                    os.system("clear")
                else:
                    print("Ok, goodbye\n")
                    break

        print(" === statistics === ")
        print(f"Played {number_tracks_played} tracks in total")
        for player in self.players_dict.values():
            print(player.name)
            print(player.stats)
            print("\n")


if __name__ == "__main__":

    os.system("clear")
    print(" ===  Welcome to Neardle, a nerdy version of Heardle  === \n\n")

    game = Game()

    game.setup_tracks_database()

    print("\nOpen your Spotify player")
    input("Press Enter to start...")
    os.system("clear")

    game.heardle_mode()
