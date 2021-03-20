# Data Gathering

## Introduction

We have two mains sources of sessions' data, the EPG and files provided by the channels. Ideally, we would get files
from all channels with the necessary information. Nonetheless, many have responded negatively, and some didn't even
respond. As such, the EPG is used for all of the channels from which we don't receive files.

## EPG

The EPG is very simple, we just need to make a request for a set of channels and a time interval. The problem is that it
provides us with very little information: the time and name of the session. This makes it hard to match a session with a
given title from a shows' database. As of right now, we search for a title's sessions simply by finding matches with its
portuguese translation and its original title.

## Files

The files require more treatment, with a specialized extraction function for each channel, but also provide us with a
lot more information. This information is sufficient for us to try and find a matching title in a shows' database.

### Processing an entry

- Find a match;
- Process the session;
- Delete outdated sessions (necessary due to updates on the listings).

### Finding a match

- [ChannelShowDataCorrection](#ChannelShowDataCorrection) is searched for a match, using: the channel id, whether it is
  a movie or not, the original title, the localized title and subgenre. In the cases of movies, the search also includes
  the director(s) and year;

    - If a match is found, the process is over.

- [ShowData](#ShowData) is searched for a match, using: the original title, whether it is a movie or not and genre. In
  the cases of movies, the search also includes the director(s) and year;

    - If a match is found, the process is over.

- A new entry is created;

- TMDB is queried for a matching title, using: the original title, the year and whether it is a movie or not. From the
  list of results, a score system is used for selecting the matching title according to the following criteria: the
  genre is valid, one of the directors is a match, the original title is an exact match (ignoring case) and the year.

    - If no match is found, repeat this step but removing the year from the query;

    - If still no match is found, the process is over.

- [ShowData](#ShowData) is now searched for a match on the selected TMDB id.

    - If a match is found, delete the newly created entry for [ShowData](#ShowData) and use the match for the remaining
      of the process;

    - If no match is found, update the new created entry in [ShowData](#ShowData) with the correct information from
      TMDB: id, director(s) and year;

- The information, from the correct entry of [ShowData](#ShowData), is compared to the one in the file and, if
  differences are found, in regard to the original title or year, a new entry
  of [ChannelShowDataCorrection](#ChannelShowDataCorrection) is created with the information from the file.

### Processing the session

- Check whether the same session already exists, in a close time period;

    - If a matching session does not exist, create a new entry;

    - If it exists, update it with the new time and update timestamp.

### Deletion of outdated sessions

- Delete all sessions whose update timestamp is older than the last half an hour (margin for the insertion of an entire
  file), for the processed time interval.