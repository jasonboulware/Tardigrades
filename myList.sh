#!/bin/bash

# Tardigrades
# CSCI 362
# FALL 2018

# The ${PWD##*/} displays the current directory name
title="${PWD##*/}"
header = "Directory Contents of ${PWD##*/}"

displayContents() {
  for file in ./*; do
    echo "<li>"
    echo "$(basename "$file")" #Removes path information
    echo "</li>"
  done
}

cat <<- _EOF_
<html>

  <head>
    <title>$title</title>
  </head>

  <body>
    <h1>$header</h1>
    <ul>
      $(displayContents)
    </ul>
  </body>
  
</html>
_EOF_
