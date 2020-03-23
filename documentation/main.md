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

- contains all the information that might be useful for a user;
- contains a search title carefully crafted to improved search results;
- *ideally it would contain a reference to Movies/Shows DB (like IMDB) so that we could perfectly match the two*.

#### Model

- id - *int* - the primary key;
- ~~show_id~~ - *string* - **change this to show_name.** This is the name of the show to which the reminder is referent to. The name the user sees;
- 