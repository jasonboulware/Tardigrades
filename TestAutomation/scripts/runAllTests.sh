#!/bin/bash

# Tardigrades
# CSCI 362
# FALL 2018


# displayContents(){

#   for dir in "TestAutomation/"*/;
#   do
#     echo "$dir"
#     for file in $dir/*;
#     do
#       echo "<ol>"
#       echo "  $(basename "$file")"
#       echo "</ol>"
      
#     done
#   done
# }



# runTests() {
#   FILECOUNTER=0;
#   FILES=testCases/*
#   SOMECOUNTER=1;
#   #read through testcases 
#   for f in $FILES; do
#     LINECOUNTER=1
#     #store each line of the test case
#     while read -r line; do
#         [[ "$line" =~ ^#.*$ ]] && continue
#           LINES[$LINECOUNTER]=$line
#           ((LINECOUNTER++))
        
#     done < $f
    
#     #give line more descriptive name
#     TESTCASE=${LINES[1]}
#     DESCRIPTION=${LINES[2]}
#     PATHTODRIVER=${LINES[3]}
#     COMPONENT=${LINES[4]}
#     DEPENDENCIES=${LINES[5]}
#     METHOD=${LINES[6]}
#     INPUT=${LINES[7]}
#     EXPECTEDOUTPUT=${LINES[8]}

#     # write expected output to oracle files
#     if [[ "$SOMECOUNTER" -lt "10" ]]; then
#         echo $EXPECTEDOUTPUT > "oracles/testCase0${SOMECOUNTER}Oracle.txt"
#     fi

#     if [[ "$SOMECOUNTER" -ge "10" ]]; then
#         echo $EXPECTEDOUTPUT > "oracles/testCase${SOMECOUNTER}Oracle.txt"
#     fi

#     TESTDRIVER="${COMPONENT}Driver"

#     # if the driver and its dependincies haven't been compiled do so
#     if [[ ! " ${COMPILEDDEPENDENCIES[@]} " =~ " ${DEPENDENCIES} " ]]; then
#       javac -Xlint:unchecked $DEPENDENCIES
#       echo "compiling ${DEPENDENCIES}"
#       COMPILEDDEPENDENCIES[$FILECOUNTER]=$DEPENDENCIES
#     fi
    
#     cd $PATHTODRIVER
#     # execute test driver 
#     java $TESTDRIVER "$METHOD" "$INPUT" "$TESTCASE"
    
#     # return to the top directory
#     cd - > /dev/null

#     ((FILECOUNTER++))
#     ((SOMECOUNTER++))
#   done
# }

#write_page()
# {
# The ${PWD##*/} displays the current directory name
#header = "Directory Contents of $0"
#title="${PWD##*/}"
# cat <<- _EOF_
# <html>

#   <head>
#     <title>$title</title>
#   </head>

#   <body>
#     <h1>$header</h1>
#     <ul>
#       $(displayContents)
#     </ul>
#   </body>
  
# </html>
# _EOF_
# }

# launch()
# {
# 	firefox testOutput.html
# }



# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
#launch
#!/bin/bash

# Tardigrades
# CSCI 362
# FALL 2018

# Team Members:
# Jason Boulware
# Austin Hollis
# Jeffery Williams
# Rowen Loucks


echo
echo AMARA TEST AUTOMATION FRAMEWORK
echo

# spacing for easier readability
TAB='  '

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

    echo Test number: "$test_number"
    echo Test Description: "$test_description"
    echo Test Function: "$func_name"
    echo Given Parameters: "$params"
    echo Expected Result: "$expected_result"
    echo Actual Result: "$TAB$actual_results"

    if [ "$actual_results" == "$expected_result" ]
        then
            echo TEST RESULT: PASS
    else
            echo TEST RESULT: FAIL
    fi

    echo
    
done


# displayContents(){

#   for dir in "TestAutomation/"*/;
#   do
#     echo "$dir"
#     for file in $dir/*;
#     do
#       echo "<ol>"
#       echo "  $(basename "$file")"
#       echo "</ol>"
#     done
#   done
# }

# runTests() {
#   FILECOUNTER=0;
#   FILES=testCases/*
#   SOMECOUNTER=1;
#   #read through testcases 
#   for f in $FILES; do
#     LINECOUNTER=1
#     #store each line of the test case
#     while read -r line; do
#         [[ "$line" =~ ^#.*$ ]] && continue
#           LINES[$LINECOUNTER]=$line
#           ((LINECOUNTER++))
        
#     done < $f
    
#     #give line more descriptive name
#     TESTCASE=${LINES[1]}
#     DESCRIPTION=${LINES[2]}
#     PATHTODRIVER=${LINES[3]}
#     COMPONENT=${LINES[4]}
#     DEPENDENCIES=${LINES[5]}
#     METHOD=${LINES[6]}
#     INPUT=${LINES[7]}
#     EXPECTEDOUTPUT=${LINES[8]}

#     # write expected output to oracle files
#     if [[ "$SOMECOUNTER" -lt "10" ]]; then
#         echo $EXPECTEDOUTPUT > "oracles/testCase0${SOMECOUNTER}Oracle.txt"
#     fi

#     if [[ "$SOMECOUNTER" -ge "10" ]]; then
#         echo $EXPECTEDOUTPUT > "oracles/testCase${SOMECOUNTER}Oracle.txt"
#     fi

#     TESTDRIVER="${COMPONENT}Driver"

#     # if the driver and its dependincies haven't been compiled do so
#     if [[ ! " ${COMPILEDDEPENDENCIES[@]} " =~ " ${DEPENDENCIES} " ]]; then
#       javac -Xlint:unchecked $DEPENDENCIES
#       echo "compiling ${DEPENDENCIES}"
#       COMPILEDDEPENDENCIES[$FILECOUNTER]=$DEPENDENCIES
#     fi
    
#     cd $PATHTODRIVER
#     # execute test driver 
#     java $TESTDRIVER "$METHOD" "$INPUT" "$TESTCASE"
    
#     # return to the top directory
#     cd - > /dev/null

#     ((FILECOUNTER++))
#     ((SOMECOUNTER++))
#   done
# }

# write_page()
# {
# # The ${PWD##*/} displays the current directory name
# #header = "Directory Contents of $0"
# #title="${PWD##*/}"
# cat <<- _EOF_
# <html>

#   <head>
#     <title>$title</title>
#   </head>

#   <body>
#     <h1>$header</h1>
#     <ul>
#       $(displayContents)
#     </ul>
#   </body>
  
# </html>
# _EOF_
# }

# launch()
# {
# 	firefox testOutput.html
# }



# ####Main

# filename=testOutput.html
# write_page > $filename
# chmod 755 $filename
# launch
