Database Migrations
===================

We use a MySQL database for Amara, which means every so often we need to update
the database schema.  This is tricky to do because we don't want to take down
the site to do this.  This means that we need to write migrations in a way that
allows both the old and new code to run at the same time.  This section has
some advice on how to do this.

The main idea is to split the migration into parts and gradually change the
schema using multiple deploys in a way that is compatible with the previous
deploy.

As an example, let's suppose we want to replace the Video.duration field, which
is an integer column, with Video.duration_string which is stored in "hh:mm:ss"
form.  Let's ignore the fact that this would be pretty silly and focus on how
this would be done.  We would split it into 4 stages:

  - **Stage 1:** Add the new field and start writing values to it:

    - Create a migration that adds the duration_string field.  Note that the
      field should have null=True, even if durations are always required,
      otherwise we'll have a database error when the old code writes rows to
      the videos table without duration_string set.
    - Add code to set the duration_string field whenever we set video durations.
    - Add a management command to update all videos and set duration_string.
      This command should be run after the old code has stopped running and
      before the stage2 code starts.
    - Continue to write to Video.duration, since the old code is relying on it.
    - Don't use the duration_string field when displaying video duration,
      since it will not be always be set.

  - **Stage 2:** Start using the new field

    - Start using duration_string for displaying the duration
    - Remove the null=True clause from the field, if necessary

  - **Stage 3:** Stop writing to the new field

    - Remove code that writes to Video.duration
    - Remove Video.duration from the Video model
    - Don't create a DB migration to remove Video.duration yet, since that
      would case an error when the code from stage2 tried to write to that
      field

  - **Stage 4:** Drop the old field

    - Create a DB migration that drops the Video.duration column

.. note::
  The same process works if you were just adding a new field, or dropping an
  old field.  In those cases you can just skip some steps.

Each stage should be in a separarate branch, typically named
``gh-[issue#]-stageX``.  We only deploy 1 stage at a time.



This process adds extra complexity when developing, but reduces the complexity
of deployment, since there's never a window when the site is down and we're
waiting for a migration to run.

It's possible that we have migrations that can't be split up like this.  If so,
that's fine, we just need to take the site down for some time period.
