CSS style guide
===============

Overview
--------

When writing CSS, we try to stick to the BEM methodology (see `BEM methodology quick start <https://en.bem.info/methodology/quick-start/>`_ ).
There's a lot to it, but the most important things for our code are.

  - **Split up CSS into self-contained components.** This helps keep things
    manageable and promotes reuse.

  - **Use a consistent naming style.** See below for our naming style.

  - **Use flat selectors instead of nested selectors.**  This means assigning
    always assigning a css class directly to the element being styled, rather
    than some rules ``.parentElement .childelement``.  There are a couple issues with
    nested selectors.  The main one is that it can be very hard to track down
    exactly which selector is causing a certain style, since any parent of an
    element can potentially affect its appearance.  The other issue is that it
    can be hard to re-use components, since if you copy code from one place to
    another, you can't be sure if the same styles will be in effect.

  - **Avoid creating per-page, or per-view styles.**  This is really an
    extension of the last guideline, but it's worth it's own section.  Say you
    want links on the dashboard view to have a certain style, you might use
    code like this: ``.dashboard-view a { ... }``.  This code is simple to
    create, but hard to maintain.  In addition to the issues pointed out above,
    we have to maintain the .dashboard-view class on the parent element, or
    else the styling would get messed up.  It makes it extremely scary to
    remove a CSS class, since you need to then check every child element.  This
    usually results in a bunch of unneeded and unmaintained CSS classes
    littering the HTML.  Instead, create a ``dashboardLink`` style and assign
    it to all links in the dashboard.  This is annoying, but less work in the
    long term.

Terminology
-----------

Components
^^^^^^^^^^

The general system is to structure the CSS into independant components.
Components can be self-contained individual elements, layout elements that
contain lots of things, or anything in-between.  Some examples of components are:

  - links
  - text blocks
  - dashboards
  - lists/tables
  - cards
  - etc.

Blocks and elements
^^^^^^^^^^^^^^^^^^^

Components are further separated into blocks and elements.  The block is the
top-level HTML element for a component.  Elements are child elements that are
work with the block to create the component.  For example, if you had a
component for a list, then the ``<ul>`` tag would be the block, and the ``<li>``
tags would be the elements.  Note that children of the ``<li>`` tags, wouldn't
be elements of list component, they would be new components.

Modifiers
^^^^^^^^^

A modifer is a CSS class that adjusts the styles of a component.  For example,
we define a button component, and have modifiers that change the look to a
primary CTA, a delete button, a disabled button, etc.

Naming
------

We use the following conventions to for CSS names:

  - We generally use camelCase for our names
  - Blocks have names like ``.myBlockName``
  - Elements have names like ``.myBlockName-myElementName``
  - Modifiers are extra CSS classes that combine with the block/elements (``.myBlockName.modifierName``)

Exceptions
----------

- BEM notation is somewhat rigid.  If there is a good reason to not use it, then feel free to make an exception.
- It's okay to use the ``>`` selector for HTML elements that have a strict
  parent/child relationship, like lists and tables.  So, even though we
  generally don't allow nested selectors, something like this is fine: ``ul.blockName > li { ... }``

Styleguide
----------

We use the styleguide `<https://amara.org/styleguide>`_ to document our
elements.  You can use that for examples of BEM in practice.

If you're adding a new element, document it with the styleguide.  There are 2 ways to do this:

 - **Django template** (preferred method):

   - Create a template in ``templates/styleguide/your-element-name.html``.  Check out the other
     templates there for examples on how to do this.
   - Add an entry to ``apps/styleguide/styleguide-toc.yml`` using a dict with the id/title keys
   - Optionally, you can also add a form for the page by creating the form
     class in ``styleguide.forms`` and adding it to
     ``styleguide.views.forms_by_section``.

 - **KSS** (legacy method):

   - Add some KSS code to the SCSS file.
   - Add an entry to ``apps/styleguide/styleguide-toc.yml`` that's just the KSS id as a string.

Legacy code
-----------
The CSS code is a work in progress and we're still working to refactor it to
use this system.  If you're working with legacy code, consider trying to
refactor it, but don't feel like you have to.
