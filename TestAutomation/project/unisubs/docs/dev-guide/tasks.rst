Tasks
=====

We use `RQ <https://github.com/rq/rq>`_ to run tasks in a separate process.

We create 3 queues:

 - **high**: high-priority queue.  This is for things that users are activily waiting for, like management form submissions.
 - **default**: default queue.  Most tasks go here
 - **low**: low-priority queue.  For example: updating video feeds.

RQ fetches tasks from the these queues, in order of priority.
