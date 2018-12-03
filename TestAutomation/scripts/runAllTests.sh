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
tab='    ' # spacing for easier readability

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
                result="<td bgcolor=\"#33cc33\">$pass</td></tr>"
        else
                result="<td bgcolor=\"#cc0000\">$fail</td></tr>"
        fi

        echo "$tab$tab$tab$tab<tr><td>$test_number</td>"
        echo "$tab$tab$tab$tab$tab<td>$test_description</td>"
        echo "$tab$tab$tab$tab$tab<td>$py_module</td>"
        echo "$tab$tab$tab$tab$tab<td>$func_name($params)</td>"
        echo "$tab$tab$tab$tab$tab<td>$expected_result</td>"
        echo "$tab$tab$tab$tab$result"


    done
}

write_page() {

    cat <<- _EOF_
    <html>
        <head>
            <title>$title</title>
            <style>
            table {
                font-family: arial, sans-serif;
                border-collapse: collapse;
                width: 100%;
                border: 2px solid black;
                border-radius: 8px;
            }
            
            h1 {
                text-align: center;
            }

            td, th {
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
                border: 2px solid black;
                border-radius: 8px;
            }

            tr:nth-child(even) {
                background-color: lightgrey;
            }
            </style>
        </head>
        <body>
            <h1>$title</h1>
            <table>
                <tr>
                    <th>Test #</th>
                    <th>Description</th>
                    <th>Module</th>
                    <th>Function</th>
                    <th>Result</th>
                    <th>Test Result</th>
                </tr>
$(insertTest)
            </table>
        </body>
    </html>
_EOF_

}

launch()
{
	firefox testOutput.html
}


# MAIN

filename=testOutput.html
write_page > "../reports/$filename"
chmod 755 "../reports/$filename"
launch