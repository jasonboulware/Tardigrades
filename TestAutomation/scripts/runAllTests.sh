#!/bin/bash

# Tardigrades
# CSCI 362
# FALL 2018

# Team Members:
# Jason Boulware
# Austin Hollis
# Jeffery Williams
# Rowen Loucks

title="AMARA TEST CASES"
pass="PASS"
fail="FAIL"

echo
echo AMARA TEST AUTOMATION FRAMEWORK
echo

# spacing for easier readability
TAB='  '
insertTest() {
    for filename in ../testCases/*; do

        # the next few lines reads lines from a text file and assigns variable names
        mapfile -t array < "$filename"
        test_number=${array[0]}
        test_description=${array[1]}
        path=${array[2]}
        py_module=${array[3]}
        func_name=${array[4]}
        params=${array[5]}
        expected_result=${array[6]}

        # this line runs the the python module given the path, the function name, and the parameters
        actual_results=$(python -c "import sys; sys.path.insert(0, '..$path'); import $py_module as m; print m.$func_name($params)")


        if [ "$actual_results" == "$expected_result" ]
            then
                echo $pass
        else
                echo $fail
        fi

        echo

    done
}

# write_page()
# {
# The ${PWD##*/} displays the current directory name
#header = "Directory Contents of $0"
#title="${PWD##*/}"

cat <<- _EOF_
<html>

  <head>
    <title>$title</title>
  </head>

  <body>
     <table>
        $(insertTest)
     </table>


    
  </body>
  
</html>
_EOF_


# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
# launch


# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
# launch


# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
# launch


# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
# launch


# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
# launch


# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
# launch
