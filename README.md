# Workona Export / Import
The excellent [Workona](https://workona.com) tool provides the ability to export your data.

Part of this data is the tabs and tab groups (called Workspaces); this tool permits you to re-import those exported tabs back  into your browser, as bookmarks.

## Use Case
For me, I wanted to copy my tabs over to a new user.  Their sharing functionality is ... designed for a different use case, and so I needed a tool.
# Install
Create a virtual environment and install the requirements:

    
    python -m venv .env
    . .env/bin/activate
    pip install -r requirements.txt

# Run
First, exort your Workona data.  Use the yaml or json format, but JSON is better.  Their YAMl export is not properly quoted, and so it can be completely broken if you use yaml control charavcters in your workspace names (like ':').  The JSON has a defect as well, where it does not guratmnee to preserve the ordering of workspacdes or tabs, but realy nobody is going to care about that (unless they are trying to develop a Workona clone, which i an not).  So do yourself a favor and use the JSON.

Then use the tool to dump that to a bookmarks.html file, and then import that intpo your browser (currently Chrtome is tested, btu this should work for Firefox).

    python gen-bookmarks.py ~/Downloads/userData-cqwklrjbcliewrbliw7ergovwegrv.json

or, for yaml:

    python gen-bookmarks.py userData-cqwklrjbcliewrbliw7ergovwegrv.txt

If you want to filter and export only one or a few of your workspaces, use `-w`:

    python gen-bookmarks.py userData-cqwklrjbcliewrbliw7ergovwegrv.json -w "My Workspace"

To import your bookmarks into Chrome, you can just go to [the following url](chrome://settings/importData):

    chrome://settings/importData

# Notes
In the code, I make sp=ome references to JSON array ordering; here is the data:

JSON spec: https://www.ecma-international.org/wp-content/uploads/ECMA-404_2nd_edition_december_2017.pdf

In section 7 (Arrays, pg 10) it states the following:

An array structure is a pair of square bracket tokens surrounding zero or more values. The values are
separated by commas. The JSON syntax does not define any specific meaning to the ordering of the values.
However, the JSON array structure is often used in situations where there is some semantics to the ordering. 
There is some followup discission [here](https://stackoverflow.com/questions/7214293/is-the-order-of-elements-in-a-json-list-preserved).
# References

1: http://fileformats.archiveteam.org/wiki/Netscape_bookmarks