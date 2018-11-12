#!/bin/bash

# Tardigrades
# CSCI 362
# FALL 2018

displayContents() {
  for file in ./*; 
  do
    echo "<li>"
    echo "$(basename "$file")"
    echo "</li>"
  done
}

write_page()
{
# The ${PWD##*/} displays the current directory name
header = "Directory Contents of ${PWD##*/}"
title="${PWD##*/}"
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
}

launch()
{
	firefox myList.html
}

####Main

filename=myList.html
write_page > $filename
chmod 755 $filename
launch
