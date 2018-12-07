=================================
Syncing and Importing
=================================

The externalsites app handles linking Amara users/teams to accounts on
externalsites.  This allows for:

* Syncing subtitles to the third party site when they are edited on Amara
* Importing new videos for the third party account

We support several sites, each works slightly differently

Youtube
=======

Both user and team accounts can be linked to YouTube accounts, but they are
handled slightly differently.  The general idea here is that the use case is
different for teams and users.  In general, teams want to have finer grained
control over what gets imported to Amara and what gets synced back to their
YouTube channel.  For users, we just import everything and sync everything.

User Accounts
-------------

* Users can link to YouTube from account section on their profile page
* A user can only link 1 YouTube account
* A YouTube account can only be linked to 1 user
* We create a video feed and import all videos for the YouTube channel.
* All subtitles for a video in that account will be synced

Team Accounts
-------------

* Teams can link to YouTube from their Settings -> Integrations page
* A team can link multiple YouTube accounts
* A YouTube account can only be linked to 1 team, but there is a way to share
  the account with other teams.
* Subtitles are normally only synced for the team's videos
* The linked team can add other teams to the syncing list, any of those team's
  videos will also be synced.
* We don't auto-import videos for the YouTube channel.
* A YouTube account can't be linked to both a team and a user

Kaltura
=======

* Teams can link to Kaltura from their Settings -> Integrations page
* Once a team links to Kaltura, subtitles on their team videos with their
  Kaltura partner id will be synced back to Kaltura.

Brightcove
==========
* Teams can link to Brightcove from their Settings -> Integrations page
* Once a team links to Brightcove, subtitles on their team videos with their
  Brightcove publisher id will be synced back to Brightcove.
* Teams can optionally choose to import videos from their Brightcove account.
* If importing, teams can either import all videos or videos matching certain
  tags.

