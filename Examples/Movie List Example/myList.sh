#!/bin/bash

# Tardigrades

#title="Directory Contents of ${PWD##*/}"

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
title="Directory Contents of ${PWD##*/}"
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
