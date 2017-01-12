# KGameHall

A game hall server support talking and playing games

# Usage

### Server

```
python GameHallServer.py [-h] [-o HOST] [-p PORT] [-n DBNAME] [-u CONNECTNUM]
                         [-d TIME_DELTA] [-l TIME_DURATION]

optional arguments:
  -h, --help	show this help message and exit
  -o, --host	Host name
  -p, --port	Server port
  -n, --dbname	Player database name
  -u, --connectnum	Number of client connection
  -d, --time_delta	21 point game time delta(in minutes)
  -l, --time_duration	21 point game time duration(in seconds)
```

### Client

python PlayerClient.py [hostname]


