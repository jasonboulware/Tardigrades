========================
HTTP Callbacks for Teams
========================

Enterprise customers can register a URL for http callbacks so that activity on their
teams will fire an HTTP POST requests to that URL.

To register your Team to receive HTTP notifications, please send your request
to us at enterprise@amara.org and we will set it up for you. You can also
contact us with inquiry about any custom notifications that are not listed in
our general offering below.

Please indicate a URL where you’d like to get notified. Each team can have
their own URL, or a common URL can be used for several teams. We recommend
that the selected URL uses HTTPS protocol for safer communication.

Notification Details
====================

We currently send notifications for the following events related to team videos and team members.

Video notifications
-------------------

Video notifications always include the following data:

- ``event``
- ``amara_video_id``
- ``youtube_video_id`` (null if the video is not hosted on YouTube)
- ``team``
- ``project``
- ``primary_team`` (used when the same callback URL is shared between multiple teams and the event that triggered callback happened on another team).

Supported events for videos:

    video-added
        Sent when a video is added to your team, or moved to your team from another team.

        Additional data: ``old_team`` (if video is moved from another team)
    video-removed
        Sent when a video is removed from your team, or moved to another team.

        Additional data: ``new_team`` (if video is moved to another team)
    video-made-primary
        Sent when one of the multiple URLs for a video on your team is set as the primary URL.

        Additional data: ``url``
    video-moved-project
        Sent when a video on your team is moved to a different project.

        Additional data: ``old_project``
    subtitles-published
        Sent when a new subtitle version for a video on your team is published.

        Additional data: ``language_code``, ``amara_version``
    subtitle-unpublished
        Sent when subtitles are deleted for a video on your team.

        Additional data: ``language_code``

Team member notifications
------------------

Team member notifications always include the following data:

- ``event``
- ``username``
- ``team``
- ``primary_team`` (used when the same callback URL is shared between multiple teams and the event that triggered callback happened on another team)

Supported events for team members:

    member-added
        Sent when a user is added to your team.
    member-removed
        Sent when a user is removed from your team.
    member-profile-changed
        Sent when the information in a team member's profile is changed.

For each event we can customize the data that is sent with the notification.

Also, all notifications are numbered. You can use the number field in the
notification to keep track of the events in your team(s).

To view previously sent notifications use the :ref:`Team Notifications API <api_notifications>`.
