The Subtitle Editor
===================

The subtitle editor is one of the larger features of amara.  It's implemented
using several components in a couple different areas:

  - The view `subtitles.views.subtitle_editor` serves up the page
  - The page runs javascript that lives in
    :file:`media/src/js/subtitle-editor`
  - We save subtitles using the API code (currently in a private repository,
    but we plan to merge it in to the main one soon)

The Experimental Editor
-----------------------

To test out large changes to the editor, we use the experimental editor.  This
means loading different JS/CSS for the editor.  Here's how to develop for it:

  - Put your code in the ``experimental-editor`` branch
  - Once you're it's ready to be used, run the ``build_experimental_editor``
    management command from that branch.  Note that you need access to AWS to
    run this, maybe the simplest way to do this is using amarashell on
    ops.pculture.io
  - Do a regular Amara deploy to finish the job
  - Once the code is ready to be merged into the main editor, just merge the branch as usual

Note that this does not affect the CSS.  If you need to make a change in the
HTML, then you need to put the code in dev.  You can use the ``experimental``
template variable to vary the HTML.


.. seealso::

    :doc:`subtitle-workflows`
