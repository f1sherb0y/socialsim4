#!/bin/bash

# A shell script to count commits and changed lines in the last 10 days,
# grouped by hour, and print a total.

# The script uses a custom format with git log to create a predictable
# output that is then processed by awk. This allows for a single pass
# to group data by hour and calculate totals.

# The magic separator "_GIT_SEPARATOR_START_" is used to mark the beginning
# of a new commit's data, which includes the hourly timestamp.
git log --since="10 days ago" --pretty=format:"_GIT_SEPARATOR_START_%n%ad" --date=format:"%Y-%m-%d %H:00" --numstat | awk '
BEGIN {
    # Initialize variables for total and hourly counts
    total_commits = 0;
    total_lines = 0;
    
    current_hour_key = "";
    hour_commits = 0;
    hour_lines = 0;
}

# This pattern matches the separator, indicating a new commit
/^_GIT_SEPARATOR_START_/ {
    # If this isn't the first commit, print the stats for the previous hour
    if (hour_commits > 0) {
        printf "    Commits: %d, Changed lines: %d\n", hour_commits, hour_lines;
    }

    # Process the new commit's date
    # The next line after the separator contains the formatted date
    getline new_hour_key;
    
    # Check if we've moved to a new hour
    if (new_hour_key != current_hour_key) {
        current_hour_key = new_hour_key;
        printf "\n%s\n", current_hour_key;
        hour_commits = 0;
        hour_lines = 0;
    }

    # Increment commit counts
    hour_commits++;
    total_commits++;
    
    # Skip to the next line to process the --numstat output
    next;
}

# This block processes the --numstat output, which contains lines and file changes
{
    # Check if the line contains three fields (insertions, deletions, filename)
    if (NF == 3 && $1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/) {
        # Add the insertions and deletions to the hourly and total counts
        hour_lines += ($1 + $2);
        total_lines += ($1 + $2);
    }
}

END {
    # Print the stats for the very last hour
    if (hour_commits > 0) {
        printf "    Commits: %d, Changed lines: %d\n", hour_commits, hour_lines;
    }
    
    # Print the final totals
    printf "\n-----------------------------------\n";
    printf "Total commits: %d\n", total_commits;
    printf "Total changed lines: %d\n", total_lines;
}