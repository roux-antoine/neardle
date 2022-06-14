import datetime as dt
import re
import sys

from difflib import SequenceMatcher


def get_real_track_name(name):
    """Attemps to get the _real_ track name

    Uses the following heuristics:
    - everything after "(" is not the real track name (e.g. "Foo bar (Live)")
    - everything after "-" is not the real track name (e.g. "Foo bar - Remastered")
    - everything after "[" is not the real track name (e.g. "Foo bar [Remix]")

    Args:
        name (str): track name to process.

    Returns:
        str: the (hopefully) real track name.
    """
    return name.split("(")[0].split(" -")[0].split(" [")[0]


def remove_accents(name):
    """Removes accents from a string

    Args:
        name (str): track name to process.

    Returns:
        str: track name without accents.
    """
    return name.translate(
        name.maketrans(
            "áàäéèëíìïòóöùúüÀÁÄÈÉËÌÍÏÒÓÖÙÚÜ", "aaaeeeiiiooouuuAAAEEEIIIOOOUUU"
        )
    )


def process_text(text):
    """Processes the input text to make it more standard

    Args:
        text (str): text to process.

    Returns:
        str: processed text.
    """
    # Remove tildes and accents, lower and remove contractions
    text = remove_accents(text).lower().replace("'", "")
    # Remove special characters
    return re.sub("[^A-Za-z0-9]+", " ", text)


def is_match(correct, guess):
    """Checks whether some subset of the guess is present in the correct answer string

    Args:
        correct (str): string of correct answer.
        guess (str): string of guess.

    Returns:
        bool: whethere there is a match.
    """
    # Process strings before comparing, then split
    correct = process_text(correct).split()
    guess = process_text(guess).split()
    # Check if all words in guess are contained in reference

    if len([x for x in guess if any([1 for y in correct if x in y])]) == len(guess):
        return True
    return False


def name_is_similar_to_existing(name, existing):
    """Checks whether some subset of the guess is present in the correct answer string

    Args:
        name (str): string to test for similarities.
        existing (List[str]): list of possible options to compare against.

    Returns:
        bool: whethere the name is similar to some strings in the existing list.
    """
    similarities_to_others = [
        SequenceMatcher(
            None, get_real_track_name(name), get_real_track_name(other_track.name)
        ).ratio()
        for other_track in existing
    ]
    if similarities_to_others and max(similarities_to_others) > 0.8:
        return True
    else:
        return False


def matching_titles(library, guess):
    """Returns the list of tracks in the library that match with the guess

    A track is considered a match if the title or the artist name matches the guess

    Args:
        guess (str): string to test for similarities.
        library (List[str]): list of possible options to compare against.

    Returns:
        List[str]: list of matches.
    """
    return [
        x.legible_name
        for x in library
        if is_match(x.name, guess) or is_match(x.artist.name, guess)
    ]


def date_in_dateframe(date, dateframe_start, dateframe_end):
    """Checks whether a data belongs to a dateframe

    Args:
        date (str): date to check.
        dateframe_start (str): start of the dateframe.
        dateframe_end (str): end of the dateframe.

    Returns:
       bool: whether the date belongs to the dateframe.
    """
    # taking everything as strings
    if len(date) == 10:
        date_format = "%Y-%m-%d"
    elif len(date) == 7:
        date_format = "%Y-%m"
    elif len(date) == 4:
        date_format = "%Y"
    else:
        print(f"Error for date: {date}")
        sys.exit()
    date_as_datetime = dt.datetime.strptime(date, date_format)
    dateframe_start_as_datetime = dt.datetime.strptime(dateframe_start, "%Y")
    dateframe_end_as_datetime = dt.datetime.strptime(dateframe_end, "%Y")

    if dateframe_start_as_datetime <= date_as_datetime <= dateframe_end_as_datetime:
        return True
    else:
        return False
