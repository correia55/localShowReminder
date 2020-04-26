# Index

- [Data model](#data-model)
- [Logic](#logic)


# Data model

## LastUpdate

Contains the date of the last update to the shows in the database.

#### Purpose

Everyday, the application queries this table to know what was the last date of which it already has shows' data for.
If this date is less than 7 days into the future, it will make new requests for shows' data up until that point.

#### Model

- id - *int* - the primary key;
- date - *date* - the date of the last update.


## Channel

Contains the information related to a Tv channel.

#### Purpose

- when making requests for shows' data, which requires the acronyms of the channels we're interested in;
- to show the name of the channel where a given tv show will air;
- the searching features (reminders and direct search) might ignore the shows of a channel with adult content, if set by the user.

#### Model

- id - *int* - the primary key;
- acronym - *string* - the acronym of the channel, which is the key used for sending the requests for show data;
- name - *string* - the name of the channel, showed to the user;
- adult - *bool* - if it has adult content or not.


## Show

Contains the information related to a Tv show session.

#### Purpose

- contains all the information that might be useful for a user;
- contains a search title carefully crafted to improved search results;
- *ideally it would contain a reference to Movies/Shows DB (like IMDB) so that we could perfectly match the two*.

#### Model

- id - *int* - the primary key;
- db_id - *string* - **to add when I have this information.** The id of the show in a Movies/Shows DB (like IMDB);
- pid - *string* - **change to source_id.** The id of the show in the webservice from where it was requested;
- ~~series_id~~ - *string* - **to remove since it is not used.** An id that represents the series of a tv show in the webservice from where it was requested;
- search_title - *string* - the title that is used when searching;
- channel_id - *int* - the foreign key to the channel where the session will take place;
- show_title - *string* - the title of the show;
- show_season - *int* - when this entry represents a tv show, this is the season of this session of the show;
- show_episode - *int* - when this entry represents a tv show, this is the episode of this session of the show;
- ~~show_details~~ - *string* - **change to show_description.** A description of the show;
- date_time - *date* - **change to start_datetime.** The datetime (date and time) of the start of a session;
- ~~duration~~ - *string* - **to remove since it is not that important.** The duration of the show.


## ShowMatch

**TODO: THIS NEEDS TO BE COMPLETED ONCE I HAVE THE ANSWERS FROM THE OPERATORS**


## DBReminder

Contains the information related to a reminder.

#### Purpose

- to get the information that needs to be searched when processing the user reminders.

#### Model

- id - *int* - the primary key;
- show_name - *string* - this is the name of the show to which the reminder is referent to. The name the user sees;
- is_movie - *bool* - if it is a movie;
- reminder_type - *int* - a number that represents the type of reminder. The type of reminder being either Listings or DB;
- show_season - *int* - the season the user is interested in;
- show_episode - *int* - the episode the user is interested in;
- user_id - *int* - a reference to the user to which the reminder belongs to;
- show_slug - *string* - when the reminder type is DB, this will contain a slug that represents the show in that DB.


## TraktTitle

Contains the information related to a possible representation of the title of show, obtained from *Trakt*.

#### Purpose

- this is used to obtain all the possible titles (in English and Portuguese) a show can have. So that these can be searched for in the listings, improving the chances of finding a match.

#### Model

- id - *int* - the primary key;
- trakt_id - *string* - the id of the show in the trakt DB;
- is_movie - *bool* - if it is a movie;
- trakt_title - *string* - the possible title, used for searching purposes.


## User

Contains the information related to a user.

#### Purpose

- this is used to know if the user wants his searches to include results from channels with adult content;
- to obtain the email to which to send the results.

#### Model

- id - *int* - the primary key;
- email - *string* - the email of the user;
- password - *string* - the hash of the password plus a random value;
- show_adult - *bool* - if the user wants his searches to include results from channels with adult content;
- verified - *bool* - if the user's email was verified;
- language - *string* - the prefered language (pt or en).


## Token

Contains the information related to the authentication tokens, used in the login.

#### Purpose

- if a refresh token is present in the database, it means that it is valid for authentication.

#### Model

- id - *int* - the primary key;
- token - *string* - a refresh token that is still valid.


# Logic

## Search Listings

#### Parameters

- search text.

#### Algorithm

**Treatment of data from listings:**

Before inserting the data from the listings to the DB, a special title is created. This title is obtained by:
 - removing all non alphanumeric characters from it;
 - replacing accented characters with the corresponding non accented character;
 - removing spaces and instead placing an underscore ('_') between words, as well as one at the start and end of the title.

**The actual search:**

The search does some of the same processing to the search query. The steps are:
 - removing all non alphanumeric characters from it;
 - replacing accented characters with the corresponding non accented character;
 - create a list of all the words in the query;
 - create a pattern which will accept any title in the DB that contains that words, in the given order. It might contain other words before and/or after the words provided in the query search, but none in between. It will also consider words a match if they are the type word plus 's' (as to consider the most common plural of portuguese words).


## Search Movies' DBs

#### Parameters

- search text;
- (optionally) whether the search is supposed to be about a movie or a tv show.

#### Algorithm

It simply creates a request to *Trakt* with the given search text and type of show and processes the results. It then uses each of the ids from IMDB to request to *OMDB* a url for a poster that represents the show.


## Processing Reminders

#### Parameters

- [the reminder](#dbreminder).

#### Algorithm

The algorithm of processing is similar to the one described in the [Search Listings](#search-listings) section. For listing reminders, the major difference is that it will consider the title as already complete, and thus, not accept words before and/or after the title in the reminder. As for the DB ones, it will work in the same way but for a list of titles obtained from Trakt.