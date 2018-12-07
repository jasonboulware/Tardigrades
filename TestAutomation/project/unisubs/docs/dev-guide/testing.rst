Testing
=======

The Amara project uses the `PyTest <http://pytest.org//>`_
testing framework.

.. _running-tests:

Running tests
-------------

To run all unittests:

::

    $ dev test

To stop after the first failure:

::

    $ dev test -x

To run tests from a single module

::

    $ dev test module.name

To run tests matching a particular pattern (matches against filenames, class
name, method/function name, pytest marks, etc).

::

    $ dev test -k [pattern]

Drop into the python debugger on errors (Very useful for debugging hard to understand failures)

::

    $ dev test --pdb

GUI Tests
---------

We also have gui tests that use selenium to automate testing with a real
browser.  These get run with the ``dev guitest`` command.  It accepts all the
same arguments as ``dev test``.  GUI tests are located in the ``guitests/``
directory.

GUITests have a special setup:

  - Before the tests run, we startup a server to test against.
  - We run the ``setup_guitests`` management commands to clear out the database
    for the test server, and auto-populate it with some data.
  - The tests themselves never access the DB.

When writing GUI tests:
  - If you need to populate the DB with some data, do it in the
    ``setup_guitests`` command.  If you are running tests from
    ``amara-enterprise`` or another submodule, you can hook into the signal
    defined in that command to populate the DB.
  - Note which TestLodge case the test is for.  Try to keep the TestLodge case
    up-to-date with the automated test.

Strategies for dealing with failing tests:

  - To see the webserver output run ``dev guitestlogs``.  Check for an exception printout there.
  - Use `dev guitest --pdb` to pause and enter the Python debugger on test
    failure.  From that command prompt you can execute selenium code.  You can
    also take that oppertunity to open the selenium console at
    http://localhost:4444/wd/hub/static/resource/hub.html, find the open
    session and look at a screenshot from the browser.
  - To start up the test webserver run ``dev up --guitests``.  This is useful
    if you want to manually step through a failing test.
  - You can also use ``dev manage --guitests``` to run management commands in
    the GUI test environment.

Javascript Tests
----------------

We use jasmine to run our javascript tests.  Use ``dev jstest`` to run them.

Writing unit tests
------------------

Unittests test the behavior of a small unit of code -- a class, small module,
etc.  We write unit tests with the following goals:

  - **To define correct behavior.**
  - **To assist initial implemenation.**  It's quicker to run unit
    tests to verify that you're code works than to manually test with a browser.
  - **To increase confidence when refactoring.**  Since the tests should
    quickly find things that broke.

When writing unit tests, try to follow these guidelines:

  - **Write tests first before code.**  See the first two points above for why
    this is useful.
  - **Have each test check 1 piece of behavior only.**  Don't add assertions that
    are checked by other tests.  On the other hand, don't feel like you need to
    follow rigid rules like 1 assertion per test.
  - **Mock out dependencies.**  This makes it so you're only testing the code-unit
    at hand, not other pieces of code.
  - **Mock out external services.**  Don't require the unittests to make network
    requests to things like the google API.  This slows down the tests and
    creates extra ways for them to fail.
  - **Document your tests.**  Make it clear what each behavior test is
    checking.  There's nothing worse than finding a failing unit test, but
    having no idea what the test was trying to do.
  - **Target a small unit of code.**  Usually tests target a
    single class or a small module in isolation.  This is good because if the
    test fails it's relatively clear which piece of code caused it.  If you
    test multiple units of code together and a test fails, then you need to
    check any of them.
  - **Put tests in the ``tests/`` directory under the app you're testing**

Writing GUI tests
-----------------

GUI tests check high-level behavior using Selenium to automate a browser.  We
write GUI tests with the following goals:

  - **Testing regressions.**  Once we know a potential way for Amara to break,
    we want to continuously test that it won't happen.  GUI tests are great for
    this.
  - **Testing integrations with amara code.**  Unittests check that each
    individual code piece is working correctly, GUI tests check that
    interactions between them.  For example we might create a unit test for the
    Video model and each of the VideoType subclasses, then we would create a
    GUI test for adding a video, which would check if those components were
    working together correctly.
  - **Testing interactions with extenal services.**  Unittests should mock out
    access to external APIs.  GUI tests don't mock them out which allows us
    catch when our code breaks because an external API change.
  - **Testing integrations with dependencies.**  When we upgrade a dependency
    like django, we want to makes sure the pages still function.
  - **Testing workflows.**  Unittests target low-level actions.  GUI tests
    target user-level actions that consist of many low-level actions together.
    Actions like logging in, adding videos, creating subtitles, consist of
    multiple low-level actions strung together.

When writing GUI tests, try to follow these guidelines:

  - **Assume the low-level logic is correct.**  Unittests are a much better way
    to test this, so don't try to test the business logic from GUI tests.  For
    example, we have lots of tests for the subtitle action system to make sure
    that works.  This means it would be good to create a GUI test that tries to
    click the buttons corresponding to the actions from the editor ("Update",
    "Save draft", "Endorse", etc.).  However, it would be a waste of time to
    try to write GUI tests to re-check the low-level logic by clicking all
    possible buttons from all possible states.
  - **Target a single user action.**  Something like logging in, adding a
    video, submitting a form, etc.
  - **Put the tests in the toplevel ```guitests/`` directory.**  Since GUI
    tests test several components together, we put them in a toplevel directory
    rather than inside an individual app.

Testers
-------

What is do testers do, given that we're trying to write all these automated
tests?  Lots of things:

  - **Exploratory testing.** Automated testing can only check for known bugs,
    testers are good at finding new bugs by interacting with Amara in
    unexpected ways.
  - **Testing user experience.** Automated testing can only check if a process
    works or not, testers can check if a process is intuitive/pleasant/simple
    for a user.
  - **Defining tests.**  Testers write up the regression tests in English, to
    provide a basis for writing the automated GUI tests.  This is not
    solely the testers resposibility though, developers can and should also write up
    tests.
  - **Verifying new functionality.** When we create new functionality, it's the
    tester's resposibility to decide when it feels good enough to merge.
  - **Regression testing :( .** Unfortunately, we have enough GUI tests to cover
    all our regression testing, so testers need to do it manually.  This should
    be fixed as soon as possible.
