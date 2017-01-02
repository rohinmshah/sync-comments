# Running the code:

    # python -u copy-comments.py >> comments.log &

The -u forces python to run in unbuffered mode, so that prints go 
straight to the comments.log file and aren't buffered.
The >> appends all output to the comments.log file.
The & makes it run in the background.

    # ps

Use this to find the job number of the newly created process.

    # disown -h [job number]

Makes it so that the process continues running after the terminal is 
closed.

# Stopping the code:

    # ps -elf

Find the job number of the running code.

    # kill [job number]

# Reading the logs:

    # tail comments.log
