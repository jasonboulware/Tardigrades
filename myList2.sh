#!/bin/bash

# Tardigrades

title="Directory Contents of ${PWD##*/}"

displayContents() {
  for file in ./*; 
  do
    echo "<li>"
    echo "$(basename "$file")"
    echo "</li>"
  done
}

cat <<- _EOF_
<html>
  <head>
    <title>
      $title
    </title>
  </head>

  <body>
    <h1>
      $title
    </h1>
    
    <ul>
      $(displayContents)
    </ul>
  </body>
</html>
_EOF_
